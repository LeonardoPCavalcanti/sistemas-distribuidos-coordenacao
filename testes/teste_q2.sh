#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "  TESTE Q2 - EXCLUSÃO MÚTUA"
echo "=========================================="

strip_ansi() { sed -r 's/\x1B\[[0-9;]*[mK]//g'; }

cleanup() {
  echo ""
  echo "Encerrando port-forwards..."
  kill "${PF0:-0}" "${PF2:-0}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Verificando pods..."
kubectl get pods | grep -E "algoritmos-coordenacao-(0|1|2)" || true
echo ""

echo "Port-forward P0 -> localhost:8080"
kubectl port-forward pods/algoritmos-coordenacao-0 8080:8080 >/dev/null 2>&1 & PF0=$!

echo "Port-forward P2 -> localhost:8082"
kubectl port-forward pods/algoritmos-coordenacao-2 8082:8080 >/dev/null 2>&1 & PF2=$!

sleep 2

echo ""
echo "Disparando pedidos concorrentes:"
echo "- Q2: P0 pede recurso"
echo "- Q2: P2 pede recurso"
(curl -s -X POST "http://127.0.0.1:8080/request-resource" >/dev/null) &
(curl -s -X POST "http://127.0.0.1:8082/request-resource" >/dev/null) &

echo ""
echo "Aguardando 16s..."
sleep 16

echo ""
echo "================================================="
echo "          EVENTOS IMPORTANTES (Q2)"
echo "================================================="

for pod in algoritmos-coordenacao-0 algoritmos-coordenacao-1 algoritmos-coordenacao-2; do
  kubectl logs "$pod" --since=10m 2>/dev/null | strip_ansi
done | grep -a -E "Pedindo acesso|Adiado pedido|ACESSO OBTIDO|TRABALHO CONCLUÍDO|Recurso liberado|Enviando REPLY" || true

echo "Teste Q2 finalizado!"
