#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "  TESTE Q1 - MULTICAST COM ATRASO"
echo "=========================================="

strip_ansi() { sed -r 's/\x1B\[[0-9;]*[mK]//g'; }

extract_processed_messages() {
  local pod="$1"
  local label="$2"
  echo "--- ${label} ---"
  kubectl logs "$pod" --since=10m 2>/dev/null \
    | strip_ansi \
    | grep -a "PROCESSADO" \
    | sed 's/^/  /' || true
  echo ""
}

cleanup() {
  echo ""
  echo "Encerrando port-forwards..."
  kill "${PF0:-0}" "${PF1:-0}" "${PF2:-0}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Verificando pods..."
kubectl get pods | grep -E "algoritmos-coordenacao-(0|1|2)" || true
echo ""

echo "Configurando port-forwards..."
kubectl port-forward pods/algoritmos-coordenacao-0 8080:8080 >/dev/null 2>&1 & PF0=$!
kubectl port-forward pods/algoritmos-coordenacao-1 8081:8080 >/dev/null 2>&1 & PF1=$!
kubectl port-forward pods/algoritmos-coordenacao-2 8082:8080 >/dev/null 2>&1 & PF2=$!

echo "⏳ Aguardando 3s..."
sleep 3
echo ""

echo "=========================================="
echo "Enviando 3 mensagens (com gatilho de atraso)"
echo "=========================================="
echo "Enviando do P0 (gatilho de atraso)..."
curl -s -X POST "http://127.0.0.1:8080/send?content=Q1%20ATRASO%20-%20Envio%20iniciado%20por%20P0%20(com%20atraso)%20(msg%20gatilho)" >/dev/null

echo "Enviando do P1..."
curl -s -X POST "http://127.0.0.1:8081/send?content=Q1%20ATRASO%20-%20Envio%20iniciado%20por%20P1%20(mensagem%20para%20todos)" >/dev/null

echo "Enviando do P2..."
curl -s -X POST "http://127.0.0.1:8082/send?content=Q1%20ATRASO%20-%20Envio%20iniciado%20por%20P2%20(mensagem%20para%20todos)" >/dev/null

echo ""
echo "Aguardando 22s (inclui atraso do ACK)..."
sleep 22

echo ""
echo "=========================================="
echo "RESULTADO: Processamento (com atraso)"
echo "=========================================="
echo ""

extract_processed_messages "algoritmos-coordenacao-0" "Processo 0"
extract_processed_messages "algoritmos-coordenacao-1" "Processo 1"
extract_processed_messages "algoritmos-coordenacao-2" "Processo 2"

echo "Teste Q1 (com atraso) finalizado!"
