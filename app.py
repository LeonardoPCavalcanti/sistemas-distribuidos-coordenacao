from flask import Flask, request, jsonify
import os
import heapq
import threading
import time

app = Flask(__name__)

# ============================================
# Configurações gerais do sistema distribuído
# ============================================

# Número de processos "lógicos" no sistema
N_PROCESSES = int(os.getenv("N_PROCESSES", "3"))

# Modo de atraso (para experimento do professor / modo hardcore)
# DELAY_MODE = "off" -> execução normal
# DELAY_MODE = "on"  -> simula atraso em ACK de um processo específico
DELAY_MODE = os.getenv("DELAY_MODE", "off").lower()

# Processo que terá ACK atrasado (se DELAY_MODE == "on")
DELAYED_PROCESS_ID = os.getenv("DELAYED_PROCESS_ID")  # ex: "2"

# Mensagem alvo do atraso (opcional).
# Se vazio ou None, qualquer mensagem daquele processo será atrasada.
DELAYED_MSG_ID = os.getenv("DELAYED_MSG_ID")  # ex: "P1-3"

# Quantos segundos de atraso no ACK, em modo hardcore
try:
    DELAY_SECONDS = float(os.getenv("DELAY_SECONDS", "5"))
except ValueError:
    DELAY_SECONDS = 5.0

# Mutex global para proteger TODAS as EDs (multicast, mutex, bully)
lock = threading.Lock()

# Relógio lógico global (Lamport simplificado)
logical_clock = 0

# ==========================
# Q1 – Multicast ordenado
# ==========================

# Fila de prioridade (heap) para mensagens pendentes de entrega.
# Cada item: (timestamp, process_id, msg_id)
holdback_queue = []  # heapq

# Tabela de mensagens: msg_id -> dados da mensagem
messages = {}  # msg_id -> { msg_id, process_id, timestamp, payload }

# Tabela de ACKs: msg_id -> set(process_ids_que_deram_ack)
ack_table = {}  # msg_id -> {1, 2, 3, ...}

# Conjunto de mensagens já entregues (apenas para histórico)
delivered = set()


def _next_timestamp(external_ts=None):
    """
    Atualiza o relógio lógico global e retorna um novo timestamp.
    Se external_ts vier preenchido, aplica a regra de Lamport:
      clock = max(clock, external_ts) + 1
    """
    global logical_clock
    with lock:
        if external_ts is not None:
            logical_clock = max(logical_clock, external_ts) + 1
        else:
            logical_clock += 1
        return logical_clock


# =======================================
# Q2 – Exclusão Mútua (algoritmo central)
# =======================================

# Dono atual da seção crítica (None se ninguém dentro)
dono_atual_mutex = None

# Fila de espera para seção crítica
fila_espera_mutex = []  # lista de process_id

# Histórico de eventos da exclusão mútua
historico_mutex = []  # ex: {"evento": "enter" | "exit", "process_id": x}


# =====================================
# Q3 – Eleição de Líder (Valentão/Bully)
# =====================================

# Conjunto de processos vivos (IDs lógicos)
processos_vivos = [1, 2, 3]

# Coordenador atual (maior ID vivo)
coordenador_atual = max(processos_vivos) if processos_vivos else None

# Flag indicando se há eleição em andamento
em_eleicao = False

# Histórico de eventos do algoritmo do Valentão
historico_eleicao = []


def _estado_bully():
    """
    Monta um snapshot legível do estado do algoritmo do Valentão.
    """
    with lock:
        vivos = list(processos_vivos)
        coord = coordenador_atual
        em_el = em_eleicao
        hist = list(historico_eleicao)

    return {
        "status": "ok",
        "coordenador": coord,
        "processos_vivos": vivos,
        "em_eleicao": em_el,
        "historico": hist,
    }


# ==========================
# Endpoints gerais / health
# ==========================

@app.route("/", methods=["GET"])
def index():
    """
    Endpoint básico para checagem de vida do serviço.
    """
    return jsonify(
        message="Algoritmo de multicast com ordenação total",
        n_processes=N_PROCESSES,
        delay_mode=DELAY_MODE,
        delayed_process_id=DELAYED_PROCESS_ID,
        delayed_msg_id=DELAYED_MSG_ID,
        delay_seconds=DELAY_SECONDS,
    )


# ======================
# Q1 – Multicast ordenado
# ======================

@app.route("/send", methods=["POST"])
def send():
    """
    Envia uma nova mensagem (multicast lógico).
    Corpo esperado (JSON):
      {
        "process_id": 1,
        "payload": "texto",
        "timestamp": 10  # opcional, para simular Lamport
      }
    """
    data = request.get_json(force=True)

    try:
        process_id = int(data["process_id"])
    except (KeyError, ValueError, TypeError):
        return jsonify(error="process_id inteiro é obrigatório"), 400

    payload = data.get("payload", "")

    external_ts = data.get("timestamp")
    if external_ts is not None:
        try:
            external_ts = int(external_ts)
        except ValueError:
            return jsonify(error="timestamp deve ser inteiro"), 400

    ts = _next_timestamp(external_ts)
    msg_id = f"P{process_id}-{ts}"

    with lock:
        messages[msg_id] = {
            "msg_id": msg_id,
            "process_id": process_id,
            "timestamp": ts,
            "payload": payload,
        }

        heapq.heappush(holdback_queue, (ts, process_id, msg_id))

        if msg_id not in ack_table:
            ack_table[msg_id] = set()
        ack_table[msg_id].add(process_id)  # remetente já conta como ACK

    print(
        f"[SEND] proc={process_id} msg_id={msg_id} ts={ts} payload={payload}",
        flush=True,
    )

    return jsonify(messages[msg_id]), 201


@app.route("/ack", methods=["POST"])
def ack():
    """
    Registra um ACK explícito para uma mensagem.
    Corpo esperado (JSON):
      {
        "process_id": 1,
        "msg_id": "P1-5"
      }
    """
    data = request.get_json(force=True)

    msg_id = data.get("msg_id")
    process_id = data.get("process_id")

    try:
        process_id = int(process_id)
    except (TypeError, ValueError):
        return jsonify(error="process_id inteiro é obrigatório"), 400

    if msg_id not in messages:
        return jsonify(error="msg_id desconhecido"), 404

    # ---------------------------
    # MODO HARDCORE (atraso ACK)
    # ---------------------------
    # Se DELAY_MODE == "on" e o process_id combinado com DELAYED_PROCESS_ID,
    # atrasamos o ACK em DELAY_SECONDS. Se DELAYED_MSG_ID estiver vazio,
    # o atraso vale para QUALQUER mensagem desse processo.
    delay_msg_match = (
        DELAYED_MSG_ID is None
        or DELAYED_MSG_ID == ""
        or msg_id == DELAYED_MSG_ID
    )

    if (
        DELAY_MODE == "on"
        and DELAYED_PROCESS_ID is not None
        and str(process_id) == str(DELAYED_PROCESS_ID)
        and delay_msg_match
    ):
        print(
            f"[ACK-DELAYED] proc={process_id} msg_id={msg_id} "
            f"(ACK atrasado em {DELAY_SECONDS} segundos - modo hardcore)",
            flush=True,
        )
        time.sleep(DELAY_SECONDS)
        # depois do sleep, segue fluxo normal para registrar o ACK

    # Registro "normal" do ACK
    with lock:
        if msg_id not in ack_table:
            ack_table[msg_id] = set()
        ack_table[msg_id].add(process_id)
        current = len(ack_table[msg_id])
        all_acks = current >= N_PROCESSES

    print(
        f"[ACK] proc={process_id} msg_id={msg_id} acks={current}/{N_PROCESSES}",
        flush=True,
    )

    return jsonify(
        status="ack_registered",
        msg_id=msg_id,
        process_id=process_id,
        current_acks=current,
        required_acks=N_PROCESSES,
        all_acks=all_acks,
    )


@app.route("/deliver", methods=["POST"])
def deliver():
    """
    Tenta entregar a próxima mensagem da fila de prioridade.
    Entrega apenas se:
      - for a mensagem no TOPO da fila (menor timestamp, desempate por process_id)
      - já tiver recebido ACK de TODOS os N_PROCESSES.
    """
    data = request.get_json(silent=True) or {}
    process_id = data.get("process_id")  # só para logs

    try:
        process_id = int(process_id) if process_id is not None else None
    except ValueError:
        return jsonify(error="process_id deve ser inteiro se informado"), 400

    with lock:
        if not holdback_queue:
            return ("", 204)

        ts, orig_pid, msg_id = holdback_queue[0]
        current_acks = len(ack_table.get(msg_id, set()))

        if current_acks < N_PROCESSES:
            return jsonify(
                status="waiting_acks",
                msg_id=msg_id,
                current_acks=current_acks,
                required_acks=N_PROCESSES,
            ), 202

        heapq.heappop(holdback_queue)
        delivered.add(msg_id)
        msg = messages[msg_id]

    print(
        f"[DELIVER] by_proc={process_id} msg_id={msg_id} ts={ts} "
        f"orig_proc={orig_pid} payload={msg['payload']}",
        flush=True,
    )

    return jsonify(
        status="delivered",
        delivered_by=process_id,
        message=msg,
    ), 200


# ==========================
# Estado completo do sistema
# ==========================

@app.route("/state", methods=["GET"])
def state():
    """
    Snapshot completo do estado:
      - Multicast (Q1)
      - Mutex centralizado (Q2)
      - Eleição de líder (Bully – Q3)
    """
    with lock:
        queue_view = [
            {"timestamp": ts, "process_id": pid, "msg_id": mid}
            for (ts, pid, mid) in holdback_queue
        ]
        acks_view = {mid: list(pset) for mid, pset in ack_table.items()}
        messages_view = list(messages.values())
        delivered_view = list(delivered)
        clock = logical_clock

        mutex_view = {
            "dono_atual": dono_atual_mutex,
            "fila_espera": list(fila_espera_mutex),
            "historico": list(historico_mutex),
        }

    bully_view = _estado_bully()
    bully_view.pop("status", None)

    return jsonify(
        n_processes=N_PROCESSES,
        logical_clock=clock,
        queue=queue_view,
        acks=acks_view,
        messages=messages_view,
        delivered=delivered_view,
        delay_mode=DELAY_MODE,
        delayed_process_id=DELAYED_PROCESS_ID,
        delayed_msg_id=DELAYED_MSG_ID,
        bully=bully_view,
        mutex=mutex_view,
    )


# =============================
# Q2 – Exclusão Mútua Central
# =============================

@app.route("/mutex/state", methods=["GET"])
def mutex_state():
    """
    Estado atual da exclusão mútua:
      - dono_atual
      - fila_espera
      - histórico de enters/exits
    """
    with lock:
        return jsonify(
            status="ok",
            descricao="Estado atual da exclusão mútua centralizada.",
            dono_atual=dono_atual_mutex,
            fila_espera=list(fila_espera_mutex),
            historico=list(historico_mutex),
        )


@app.route("/mutex/request", methods=["POST"])
def mutex_request():
    """
    Processo pede para entrar na seção crítica.
    Corpo esperado (JSON):
      {
        "process_id": 1
      }
    """
    data = request.get_json(force=True)

    try:
        process_id = int(data["process_id"])
    except (KeyError, TypeError, ValueError):
        return jsonify(error="process_id inteiro é obrigatório"), 400

    global dono_atual_mutex

    with lock:
        global historico_mutex

        if dono_atual_mutex is None:
            dono_atual_mutex = process_id
            historico_mutex.append({"evento": "enter", "process_id": process_id})

            return jsonify(
                status="granted",
                descricao=f"Processo {process_id} entrou na seção crítica.",
                dono_atual=dono_atual_mutex,
                fila_espera=list(fila_espera_mutex),
                granted=True,
            )

        if dono_atual_mutex == process_id:
            return jsonify(
                status="already_owner",
                descricao=(
                    f"Processo {process_id} já é o dono atual da seção crítica."
                ),
                dono_atual=dono_atual_mutex,
                fila_espera=list(fila_espera_mutex),
                granted=True,
            )

        if process_id not in fila_espera_mutex:
            fila_espera_mutex.append(process_id)

        pos = fila_espera_mutex.index(process_id) + 1

        return jsonify(
            status="waiting",
            descricao=(
                f"Processo {process_id} está aguardando na fila para entrar "
                "na seção crítica."
            ),
            dono_atual=dono_atual_mutex,
            fila_espera=list(fila_espera_mutex),
            granted=False,
            posicao_na_fila=pos,
        )


@app.route("/mutex/release", methods=["POST"])
def mutex_release():
    """
    Processo libera a seção crítica.
    Corpo esperado (JSON):
      {
        "process_id": 1
      }
    """
    data = request.get_json(force=True)

    try:
        process_id = int(data["process_id"])
    except (KeyError, TypeError, ValueError):
        return jsonify(error="process_id inteiro é obrigatório"), 400

    global dono_atual_mutex

    with lock:
        global historico_mutex

        if dono_atual_mutex != process_id:
            return jsonify(
                status="error",
                descricao=(
                    "Apenas o processo que está na seção crítica pode liberá-la."
                ),
                erro="processo não é o dono atual da seção crítica",
                dono_atual=dono_atual_mutex,
            ), 400

        historico_mutex.append({"evento": "exit", "process_id": process_id})
        dono_anterior = process_id

        if fila_espera_mutex:
            novo_dono = fila_espera_mutex.pop(0)
            dono_atual_mutex = novo_dono
            historico_mutex.append({"evento": "enter", "process_id": novo_dono})

            return jsonify(
                status="released",
                descricao=(
                    f"Processo {process_id} liberou a seção crítica. "
                    f"Processo {novo_dono} agora é o novo dono."
                ),
                dono_anterior=dono_anterior,
                novo_dono=novo_dono,
                fila_espera=list(fila_espera_mutex),
            )

        dono_atual_mutex = None

        return jsonify(
            status="released",
            descricao=(
                f"Processo {process_id} liberou a seção crítica. "
                "Nenhum processo na fila, seção crítica ficou livre."
            ),
            dono_anterior=dono_anterior,
            novo_dono=None,
            fila_espera=list(fila_espera_mutex),
        )


# =====================================
# Q3 – Eleição de Líder (Valentão/Bully)
# =====================================

@app.route("/bully/election", methods=["POST"])
def bully_eleicao():
    """
    Inicia uma eleição pelo algoritmo do Valentão.
    Corpo esperado (JSON):
      {
        "process_id": 1
      }
    """
    data = request.get_json(force=True)

    try:
        process_id = int(data["process_id"])
    except (KeyError, TypeError, ValueError):
        return jsonify(error="process_id inteiro é obrigatório"), 400

    global coordenador_atual, em_eleicao

    with lock:
        if process_id not in processos_vivos:
            return jsonify(
                status="error",
                descricao=f"Processo {process_id} não está vivo, não pode iniciar eleição.",
            ), 400

        em_eleicao = True
        passos = []

        passos.append(
            {"tipo": "eleicao", "descricao": f"Processo {process_id} iniciou uma eleição."}
        )

        candidatos = [p for p in processos_vivos if p > process_id]

        if not candidatos:
            coordenador_atual = process_id
            em_eleicao = False

            passos.append(
                {
                    "tipo": "eleicao",
                    "descricao": (
                        f"Processo {process_id} é o maior ID vivo e foi eleito coordenador."
                    ),
                }
            )
            historico_eleicao.extend(passos)

            return jsonify(
                status="ok",
                coordenador=coordenador_atual,
                processos_vivos=list(processos_vivos),
                em_eleicao=False,
                iniciado_por=process_id,
                passos=passos,
            )

        for c in sorted(candidatos):
            passos.append(
                {
                    "tipo": "msg",
                    "categoria": "ELECTION",
                    "de": process_id,
                    "para": c,
                    "descricao": (
                        f"Processo {process_id} envia mensagem ELECTION para processo {c}."
                    ),
                }
            )
            passos.append(
                {
                    "tipo": "msg",
                    "categoria": "OK",
                    "de": c,
                    "para": process_id,
                    "descricao": (
                        f"Processo {c} responde OK para processo {process_id}."
                    ),
                }
            )

        novo_coord = max(candidatos)
        coordenador_atual = novo_coord
        em_eleicao = False

        for p in processos_vivos:
            if p == novo_coord:
                continue
            passos.append(
                {
                    "tipo": "msg",
                    "categoria": "COORDINATOR",
                    "de": novo_coord,
                    "para": p,
                    "descricao": (
                        f"Processo {novo_coord} anuncia que é o novo coordenador para o processo {p}."
                    ),
                }
            )

        passos.append(
            {
                "tipo": "eleicao",
                "descricao": (
                    f"Processo {novo_coord} foi eleito coordenador pelo algoritmo do Valentão."
                ),
            }
        )

        historico_eleicao.extend(passos)

        return jsonify(
            status="ok",
            coordenador=coordenador_atual,
            processos_vivos=list(processos_vivos),
            em_eleicao=False,
            iniciado_por=process_id,
            passos=passos,
        )


@app.route("/bully/coordinator", methods=["GET"])
def bully_coordenador():
    """
    Retorna quem é o coordenador atual e quais processos estão vivos.
    """
    with lock:
        return jsonify(
            status="ok",
            coordenador=coordenador_atual,
            processos_vivos=list(processos_vivos),
        )


@app.route("/bully/state", methods=["GET"])
def bully_estado():
    """
    Snapshot completo do estado do algoritmo do Valentão.
    """
    return jsonify(_estado_bully())


@app.route("/bully/fail", methods=["POST"])
def bully_falha_processo():
    """
    Simula a falha de um processo (fica "offline").
    Corpo esperado (JSON):
      {
        "process_id": 3
      }
    """
    data = request.get_json(force=True)

    try:
        process_id = int(data["process_id"])
    except (KeyError, TypeError, ValueError):
        return jsonify(error="process_id inteiro é obrigatório"), 400

    global coordenador_atual

    with lock:
        if process_id not in processos_vivos:
            return jsonify(
                status="error",
                descricao=f"Processo {process_id} já está marcado como falho.",
            ), 400

        processos_vivos.remove(process_id)

        historico_eleicao.append(
            {
                "tipo": "falha",
                "descricao": f"Processo {process_id} foi marcado como falho (offline).",
            }
        )

        if coordenador_atual == process_id:
            coordenador_anterior = coordenador_atual
            coordenador_atual = None
            historico_eleicao.append(
                {
                    "tipo": "coordenador",
                    "descricao": (
                        f"O coordenador {coordenador_anterior} falhou. "
                        "O sistema está sem coordenador até a próxima eleição."
                    ),
                }
            )

        return jsonify(
            status="ok",
            descricao=f"Processo {process_id} foi marcado como falho (offline).",
            processos_vivos=list(processos_vivos),
            coordenador=coordenador_atual,
        )


@app.route("/bully/recover", methods=["POST"])
def bully_recupera_processo():
    """
    Simula a recuperação de um processo (volta a ficar "vivo").
    Corpo esperado (JSON):
      {
        "process_id": 3
      }
    """
    data = request.get_json(force=True)

    try:
        process_id = int(data["process_id"])
    except (KeyError, TypeError, ValueError):
        return jsonify(error="process_id inteiro é obrigatório"), 400

    with lock:
        if process_id not in processos_vivos:
            processos_vivos.append(process_id)
            processos_vivos.sort()
            historico_eleicao.append(
                {
                    "tipo": "recuperacao",
                    "descricao": (
                        f"Processo {process_id} foi marcado como vivo (recuperado)."
                    ),
                }
            )

        return jsonify(
            status="ok",
            descricao=f"Processo {process_id} foi marcado como vivo (recuperado).",
            processos_vivos=list(processos_vivos),
            coordenador=coordenador_atual,
        )


if __name__ == "__main__":
    # Rodando localmente (fora do Kubernetes)
    app.run(host="0.0.0.0", port=8080)
