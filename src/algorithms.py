import asyncio
import heapq
import threading
import time
from typing import Dict, List, Any, Optional

from src.config import TOTAL_PROCESSES, PROCESS_ID
from src.logging_config import logger
from src.schemas import Message


# =========================================================
# Utilit\00e1rios / Estado comum
# =========================================================

_lock = threading.Lock()
LOGICAL_CLOCK: int = int(time.time() % 10)

def get_clock() -> int:
    with _lock:
        return LOGICAL_CLOCK

def update_clock(received_ts: int = 0) -> int:
    global LOGICAL_CLOCK
    with _lock:
        if received_ts > LOGICAL_CLOCK:
            LOGICAL_CLOCK = received_ts + 1
        else:
            LOGICAL_CLOCK += 1
        return LOGICAL_CLOCK


# =========================================================
# Q1 - Multicast com ordena\00e7\00e3o total (Lamport)
# =========================================================

PENDING_QUEUE: List[Any] = []
ACK_COUNT: Dict[str, int] = {}


def _try_deliver():
    while True:
        with _lock:
            if not PENDING_QUEUE:
                return
            ts, sender_id, msg_id, msg = PENDING_QUEUE[0]
            count = ACK_COUNT.get(msg_id, 0)

        if count >= TOTAL_PROCESSES:
            with _lock:
                heapq.heappop(PENDING_QUEUE)
                ACK_COUNT.pop(msg_id, None)

            logger.success(
                f"PROCESSADO! Conte\00fado: '{msg.content}' "
                f"(ID: {msg.message_id}, TS Original: {msg.timestamp}, Ordem: ({ts},{sender_id}))"
            )
        else:
            return


async def receive_message(message: Message):
    from src.http_client import send_acks_to_all_peers

    # atualiza rel\00f3gio local, mas mant\00e9m ordena\00e7\00e3o pelo TS original
    update_clock(message.timestamp)

    with _lock:
        heapq.heappush(PENDING_QUEUE, (message.timestamp, message.sender_id, message.message_id, message))
        ACK_COUNT[message.message_id] = ACK_COUNT.get(message.message_id, 0) + 1

    await send_acks_to_all_peers(message.message_id)
    _try_deliver()


def receive_ack(message_id: str):
    update_clock()

    with _lock:
        ACK_COUNT[message_id] = ACK_COUNT.get(message_id, 0) + 1
        logger.info(f"ACK para {message_id}: {ACK_COUNT[message_id]}/{TOTAL_PROCESSES}")

    _try_deliver()


# =========================================================
# Q2 - Exclus\00e3o M\00fatua (Ricart & Agrawala)
# =========================================================

RESOURCE_IN_USE = False
WAITING = False
REQUEST_TS = -1
PENDING_REPLIES = 0
DEFERRED: List[int] = []

REPLY_EVENT: Optional[asyncio.Event] = None


def init_async_primitives():
    global REPLY_EVENT
    if REPLY_EVENT is None:
        REPLY_EVENT = asyncio.Event()
        logger.info("Primitivas asyncio inicializadas (REPLY_EVENT).")


async def request_resource():
    from src.http_client import send_request_to_peers

    global WAITING, REQUEST_TS, PENDING_REPLIES

    ts = update_clock()

    with _lock:
        if RESOURCE_IN_USE or WAITING:
            logger.warning("Pedido ignorado: recurso em uso ou j\00e1 aguardando.")
            return

        WAITING = True
        REQUEST_TS = ts
        PENDING_REPLIES = TOTAL_PROCESSES - 1

        if REPLY_EVENT:
            REPLY_EVENT.clear()

        logger.info(f"Pedindo acesso ao recurso TS={REQUEST_TS}. Faltam {PENDING_REPLIES} respostas.")

    await send_request_to_peers(REQUEST_TS)

    if PENDING_REPLIES == 0:
        await _enter_cs()
        return

    logger.info("Aguardando todos os REPLYs...")
    if REPLY_EVENT:
        await REPLY_EVENT.wait()

    await _enter_cs()


async def handle_request(request_ts: int, requester_id: int):
    from src.http_client import send_reply

    global DEFERRED

    update_clock(request_ts)

    with _lock:
        should_reply = (
            (not RESOURCE_IN_USE and not WAITING)
            or (
                WAITING and (
                    request_ts < REQUEST_TS
                    or (request_ts == REQUEST_TS and requester_id < PROCESS_ID)
                )
            )
        )

        if not should_reply:
            logger.warning(
                f"REPLY adiado para P{requester_id} (TS={request_ts}). "
                f"Meu TS={REQUEST_TS}"
            )
            DEFERRED.append(requester_id)

    if should_reply:
        logger.info(f"Respondendo REPLY para P{requester_id}.")
        await send_reply(requester_id)


async def handle_reply():
    global PENDING_REPLIES

    with _lock:
        if not WAITING:
            logger.warning("REPLY recebido mas n\00e3o estava aguardando.")
            return

        PENDING_REPLIES -= 1
        logger.info(f"REPLY recebido. Faltam {PENDING_REPLIES} respostas.")

        if PENDING_REPLIES == 0 and REPLY_EVENT:
            REPLY_EVENT.set()


async def _enter_cs():
    global WAITING, RESOURCE_IN_USE

    with _lock:
        WAITING = False
        RESOURCE_IN_USE = True

    logger.success(">>> ACESSO OBTIDO! Entrando na Regi\00e3o Cr\00edtica. <<<")
    await asyncio.sleep(5)
    logger.success(">>> TRABALHO CONCLU\00cdDO! Saindo da Regi\00e3o Cr\00edtica. <<<")

    await _release_resource()


async def _release_resource():
    from src.http_client import send_reply

    global RESOURCE_IN_USE, DEFERRED

    with _lock:
        RESOURCE_IN_USE = False
        to_reply = list(DEFERRED)
        DEFERRED.clear()

    logger.info(f"Recurso liberado. Enviando {len(to_reply)} replies adiados.")
    for pid in to_reply:
        await send_reply(pid)


# =========================================================
# Q3 - Elei\00e7\00e3o de L\00edder (Bully)
# =========================================================

LEADER_STATE = "FOLLOWER"
CURRENT_LEADER = None
ELECTION_IN_PROGRESS = False
ANSWERS: List[int] = []


async def start_election():
    from src.http_client import send_election_to_higher_peers, send_coordinator

    global LEADER_STATE, CURRENT_LEADER, ELECTION_IN_PROGRESS, ANSWERS

    with _lock:
        if ELECTION_IN_PROGRESS:
            logger.warning("Eleição já em progresso.")
            return
        ELECTION_IN_PROGRESS = True
        LEADER_STATE = "CANDIDATE"
        ANSWERS = []
        logger.info(f">>> INICIANDO ELEI\00c7\00c3O <<< P{PROCESS_ID} candidatando.")

    await send_election_to_higher_peers()

    timeout = 3
    await asyncio.sleep(timeout)

    with _lock:
        if len(ANSWERS) == 0:
            LEADER_STATE = "LEADER"
            CURRENT_LEADER = PROCESS_ID
            ELECTION_IN_PROGRESS = False
            logger.success(f">>> NOVO L\00cdDER ELEITO <<< P{PROCESS_ID} \00e9 o l\00edder!")
        else:
            LEADER_STATE = "FOLLOWER"
            ELECTION_IN_PROGRESS = False
            return

    await send_coordinator(PROCESS_ID)


async def handle_election(candidate_id: int):
    from src.http_client import send_answer

    if PROCESS_ID > candidate_id:
        logger.info(f"P{PROCESS_ID} > P{candidate_id}: enviando ANSWER e iniciando elei\00e7\00e3o.")
        await send_answer(candidate_id)

        with _lock:
            already = ELECTION_IN_PROGRESS

        if not already:
            await start_election()
    else:
        logger.info(f"P{PROCESS_ID} <= P{candidate_id}: aguardando COORDINATOR.")


async def handle_answer(peer_id: int):
    global ANSWERS
    with _lock:
        if peer_id not in ANSWERS:
            ANSWERS.append(peer_id)
            logger.info(f"ANSWER recebido de P{peer_id}. Total: {len(ANSWERS)}")


async def handle_coordinator(leader_id: int):
    global CURRENT_LEADER, LEADER_STATE, ELECTION_IN_PROGRESS
    with _lock:
        CURRENT_LEADER = leader_id
        LEADER_STATE = "FOLLOWER"
        ELECTION_IN_PROGRESS = False
    logger.success(f">>> COORDINATOR <<< L\00edder P{leader_id} (notificado para P{PROCESS_ID}).")
