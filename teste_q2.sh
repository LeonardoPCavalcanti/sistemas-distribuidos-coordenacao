#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:8080}

pretty_json() {
  local body="$1"
  echo "$body" | python -m json.tool 2>/dev/null || echo "$body"
}

echo "==== Q2 - Estado inicial da exclusão mútua (/mutex/state) ===="
RESP=$(curl -s "${BASE_URL}/mutex/state")
pretty_json "$RESP"
echo

echo "==== Q2 - Processo 1 pedindo seção crítica (/mutex/request) ===="
RESP=$(curl -s -X POST "${BASE_URL}/mutex/request" \
  -H "Content-Type: application/json" \
  -d '{"process_id": 1}')
pretty_json "$RESP"
echo
echo

echo "==== Q2 - Processo 2 pedindo seção crítica (vai pra fila) (/mutex/request) ===="
RESP=$(curl -s -X POST "${BASE_URL}/mutex/request" \
  -H "Content-Type: application/json" \
  -d '{"process_id": 2}')
pretty_json "$RESP"
echo
echo

echo "==== Q2 - Estado após pedidos de 1 e 2 (/mutex/state) ===="
RESP=$(curl -s "${BASE_URL}/mutex/state")
pretty_json "$RESP"
echo
echo

echo "==== Q2 - Processo 1 liberando seção crítica (/mutex/release) ===="
RESP=$(curl -s -X POST "${BASE_URL}/mutex/release" \
  -H "Content-Type: application/json" \
  -d '{"process_id": 1}')
pretty_json "$RESP"
echo
echo

echo "==== Q2 - Estado final (/mutex/state) ===="
RESP=$(curl -s "${BASE_URL}/mutex/state")
pretty_json "$RESP"
echo
echo

echo "==== Q2 - (Opcional) Erro: processo 1 tenta liberar sem ser o dono ===="
RESP=$(curl -s -X POST "${BASE_URL}/mutex/release" \
  -H "Content-Type: application/json" \
  -d '{"process_id": 1}')
pretty_json "$RESP"
echo
