import os
import sys
from loguru import logger

logger.remove()

log_format = (
    "<green>{time:HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[process_name]: <12}</cyan> | "
    "<level>{message}</level>"
)

logger.add(sys.stderr, format=log_format, level="INFO", colorize=True)


def _process_name():
    pod = os.environ.get("POD_NAME", "local-0")
    try:
        pid = int(pod.split("-")[-1])
        return f"Processo-{pid}"
    except Exception:
        return "Local"


logger.configure(extra={"process_name": _process_name()})

__all__ = ["logger"]
