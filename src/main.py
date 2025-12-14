import asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.config import PROCESS_ID
from src.logging_config import logger
from src import algorithms as alg

from src.routes.q1_multicast import router as q1_router
from src.routes.q2_mutex import router as q2_router
from src.routes.q3_election import router as q3_router

app = FastAPI(title=f"Processo P{PROCESS_ID} - Algoritmos Distribu\00eddos")

_background_tasks = set()


def run_bg(coro):
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


@app.on_event("startup")
async def on_startup():
    # Cria primitivas asyncio no loop correto (evita: "no current event loop in AnyIO thread")
    alg.init_async_primitives()
    logger.info(f"Startup conclu\00eddo no P{PROCESS_ID}.")


@app.get("/")
def health():
    return {
        "process_id": PROCESS_ID,
        "clock": alg.get_clock(),
        "status": "Running",
    }


# registra routers (mantendo os endpoints originais)
app.include_router(q1_router)
app.include_router(q2_router)
app.include_router(q3_router)


# Exponho helper para rotas usarem de forma limpa
@app.post("/_bg")
async def _debug_bg():
    # endpoint interno (n\00e3o usado em testes) apenas para debug
    return JSONResponse({"ok": True})
