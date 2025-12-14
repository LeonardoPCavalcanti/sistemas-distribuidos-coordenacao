from fastapi import APIRouter

from src.logging_config import logger
import src.algorithms as alg

router = APIRouter()


@router.post("/start-election", status_code=202)
async def start_election():
    logger.info("Endpoint /start-election chamado.")
    await alg.start_election()
    return {"status": "Election started."}


@router.post("/receive-election", status_code=202)
async def receive_election(candidate_id: int):
    logger.info(f"Recebido ELECTION de P{candidate_id}")
    await alg.handle_election(candidate_id)
    return {"status": "Election message received."}


@router.post("/receive-answer", status_code=202)
async def receive_answer(peer_id: int):
    logger.info(f"Recebido ANSWER de P{peer_id}")
    await alg.handle_answer(peer_id)
    return {"status": "Answer received."}


@router.post("/receive-coordinator", status_code=202)
async def receive_coordinator(leader_id: int):
    logger.info(f"Recebido COORDINATOR: l\00edder=P{leader_id}")
    await alg.handle_coordinator(leader_id)
    return {"status": "Coordinator received."}
