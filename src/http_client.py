import asyncio
import httpx

from src.config import PEERS, PEER_PORT, PROCESS_ID
from src.logging_config import logger
from src.schemas import Message, Ack, SCRequest


# -------------------------------
# Q1 - Multicast
# -------------------------------

async def send_message_to_peers(message: Message):
    my_fqdn = PEERS[PROCESS_ID]
    logger.info(f"Enviando mensagem {message.message_id} para os pares.")
    async with httpx.AsyncClient() as client:
        for peer in PEERS:
            if peer == my_fqdn:
                continue
            url = f"http://{peer}:{PEER_PORT}/message"
            try:
                await client.post(url, json=message.model_dump(), timeout=5.0)
            except httpx.RequestError as e:
                logger.error(f"Falha ao enviar mensagem para {peer}: {e}")


async def send_acks_to_all_peers(message_id: str):
    my_fqdn = PEERS[PROCESS_ID]
    ack_msg = Ack(message_id=message_id, process_id=PROCESS_ID)

    # Gatilho de atraso (mantido)
    delay_msg_id = "MSG_PARA_ATRASAR"
    delay_proc_id = 2
    delay_seconds = 5

    if message_id == delay_msg_id and PROCESS_ID == delay_proc_id:
        logger.warning(f"ATRASO INDUZIDO: Atrasando ACK de {message_id} por {delay_seconds}s...")
        await asyncio.sleep(delay_seconds)

    async with httpx.AsyncClient() as client:
        for peer in PEERS:
            if peer == my_fqdn:
                continue
            url = f"http://{peer}:{PEER_PORT}/ack"
            try:
                await client.post(url, json=ack_msg.model_dump(), timeout=5.0)
            except httpx.RequestError as e:
                logger.error(f"Falha ao enviar ACK para {peer}: {e}")


# -------------------------------
# Q2 - Ricart & Agrawala
# -------------------------------

async def send_request_to_peers(request_ts: int):
    my_fqdn = PEERS[PROCESS_ID]
    payload = SCRequest(request_ts=request_ts, process_id=PROCESS_ID)

    logger.info(f"Enviando REQUEST (TS={request_ts}) para todos os pares.")
    async with httpx.AsyncClient() as client:
        for peer in PEERS:
            if peer == my_fqdn:
                continue
            url = f"http://{peer}:{PEER_PORT}/receive-request"
            try:
                await client.post(url, json=payload.model_dump(), timeout=5.0)
            except httpx.RequestError as e:
                logger.error(f"Falha ao enviar REQUEST para {peer}: {e}")


async def send_reply(target_peer_id: int):
    target_peer = PEERS[target_peer_id]
    url = f"http://{target_peer}:{PEER_PORT}/receive-reply"
    params = {"sender_id": PROCESS_ID}

    logger.info(f"Enviando REPLY para {target_peer}.")
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, params=params, timeout=5.0)
        except httpx.RequestError as e:
            logger.error(f"Falha ao enviar REPLY para {target_peer}: {e}")


# -------------------------------
# Q3 - Bully
# -------------------------------

async def send_election_to_higher_peers():
    my_fqdn = PEERS[PROCESS_ID]
    logger.info(f"P{PROCESS_ID} enviando ELECTION para IDs maiores.")

    async with httpx.AsyncClient() as client:
        for peer in PEERS:
            if peer == my_fqdn:
                continue

            # extrai id do hostname do peer: "...-2.<service>"
            hostname = peer.split(".")[0]
            peer_id = int(hostname.split("-")[-1])

            if peer_id > PROCESS_ID:
                url = f"http://{peer}:{PEER_PORT}/receive-election"
                params = {"candidate_id": PROCESS_ID}
                try:
                    await client.post(url, params=params, timeout=5.0)
                    logger.info(f"ELECTION enviado para P{peer_id}.")
                except httpx.RequestError as e:
                    logger.error(f"Falha ao enviar ELECTION para {peer}: {e}")


async def send_answer(candidate_id: int):
    target_peer = PEERS[candidate_id]
    url = f"http://{target_peer}:{PEER_PORT}/receive-answer"
    params = {"peer_id": PROCESS_ID}

    logger.info(f"P{PROCESS_ID} enviando ANSWER para P{candidate_id}.")
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, params=params, timeout=5.0)
        except httpx.RequestError as e:
            logger.error(f"Falha ao enviar ANSWER para {target_peer}: {e}")


async def send_coordinator(leader_id: int):
    my_fqdn = PEERS[PROCESS_ID]
    logger.info(f"Enviando COORDINATOR (L\00edder: P{leader_id}) para todos os pares.")

    async with httpx.AsyncClient() as client:
        for peer in PEERS:
            if peer == my_fqdn:
                continue
            url = f"http://{peer}:{PEER_PORT}/receive-coordinator"
            params = {"leader_id": leader_id}
            try:
                await client.post(url, params=params, timeout=5.0)
            except httpx.RequestError as e:
                logger.error(f"Falha ao enviar COORDINATOR para {peer}: {e}")
