from fastapi import APIRouter

from src.logging_config import logger
from src.schemas import SCRequest
import src.algorithms as alg

router = APIRouter()


@router.post("/request-resource", status_code=202)
async def request_resource():
    logger.info("Endpoint /request-resource chamado.")
    await alg.request_resource()
    return {"status": "Request initiated."}


@router.post("/receive-request", status_code=202)
async def receive_request(req: SCRequest):
    logger.info(f"Recebido REQUEST de P{req.process_id} TS={req.request_ts}")
    await alg.handle_request(req.request_ts, req.process_id)
    return {"status": "Request received."}


@router.post("/receive-reply", status_code=202)
async def receive_reply(sender_id: int):
    logger.info(f"Recebido REPLY de P{sender_id}")
    await alg.handle_reply()
    return {"status": "Reply received."}
