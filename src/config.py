import os

# ---------------------------------------------------------
# Identidade do processo no StatefulSet (POD_NAME = "...-0")
# ---------------------------------------------------------
pod_name = os.getenv("POD_NAME", "algoritmos-coordenacao-0")
try:
    PROCESS_ID = int(pod_name.split("-")[-1])
except Exception:
    PROCESS_ID = 0

# ---------------------------------------------------------
# Configura\00e7\00f5es gerais
# ---------------------------------------------------------
TOTAL_PROCESSES = int(os.getenv("TOTAL_PROCESSES", "3"))
PEER_PORT = int(os.getenv("PEER_PORT", "8080"))

# ---------------------------------------------------------
# DNS dos peers no Kubernetes (StatefulSet + Headless Service)
# Ex: algoritmos-coordenacao-0.algoritmos-coordenacao-service
# ---------------------------------------------------------
STATEFULSET_NAME = os.getenv("STATEFULSET_NAME", "algoritmos-coordenacao")
SERVICE_NAME = os.getenv("SERVICE_NAME", "algoritmos-coordenacao-service")

PEERS = [
    f"{STATEFULSET_NAME}-{i}.{SERVICE_NAME}"
    for i in range(TOTAL_PROCESSES)
]
