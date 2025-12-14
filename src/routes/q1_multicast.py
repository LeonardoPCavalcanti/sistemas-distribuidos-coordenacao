import uuid
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.config import PROCESS_ID
from src.logging_config import logger
from src.schemas import Message, Ack
import src.algorithms as alg
from src.http_client import send_message_to_peers

router = APIRouter()


@router.post("/message")
async def receive_message(message: Message):
    logger.info(f"Recebido MESSAGE de P{message.sender_id} (TS={message.timestamp})")
    await alg.receive_message(message)
    return {"status": "Message received."}


@router.post("/ack")
async def receive_ack(ack: Ack):
    logger.info(f"Recebido ACK para {ack.message_id} (de P{ack.process_id})")
    alg.receive_ack(ack.message_id)
    return {"status": "ACK processed."}


@router.post("/send")
async def send_multicast_message(content: str):
    # gatilho de atraso
    is_delayed = "com atraso" in content.lower()
    msg_id = "MSG_PARA_ATRASAR" if is_delayed else str(uuid.uuid4())

    ts = alg.update_clock()
    msg = Message(
        sender_id=PROCESS_ID,
        message_id=msg_id,
        timestamp=ts,
        content=content
    )

    logger.info(f"Iniciando multicast id={msg.message_id} ts={msg.timestamp}")

    # envia para os peers
    await send_message_to_peers(msg)

    # entrega local
    await alg.receive_message(msg)

    return JSONResponse(
        content={"status": "Multicast initiated", "message_id": msg.message_id},
        status_code=200
    )
