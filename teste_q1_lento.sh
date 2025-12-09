#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:8080}

pretty_json() {
  local body="$1"
  echo "$body" | python -m json.tool 2>/dev/null || echo "$body"
}

echo "==== Q1 (LENTO) - Estado inicial (/state) ===="
RESP=$(curl -s "${BASE_URL}/state")
pretty_json "$RESP"
echo

echo "==== Q1 (LENTO) - Enviando mensagem do processo 1 (/send) ===="

RESP=$(curl -s -X POST "${BASE_URL}/send" \
  -H "Content-Type: application/json" \
  -d '{"process_id": 1, "payload": "mensagem-lenta"}')

pretty_json "$RESP"
echo

MSG_ID=$(echo "$RESP" | python -c 'import sys, json; print(json.load(sys.stdin)["msg_id"])')
echo ">> msg_id capturado: ${MSG_ID}"
echo

echo "==== Q1 (LENTO) - ACK normal de proc 1 e 3, proc 2 AINDA NAO responde ===="

echo "-> ACK proc 1"
RESP=$(curl -s -X POST "${BASE_URL}/ack" \
  -H "Content-Type: application/json" \
  -d "{\"process_id\": 1, \"msg_id\": \"${MSG_ID}\"}")
pretty_json "$RESP"
echo
echo

echo "-> ACK proc 3"
RESP=$(curl -s -X POST "${BASE_URL}/ack" \
  -H "Content-Type: application/json" \
  -d "{\"process_id\": 3, \"msg_id\": \"${MSG_ID}\"}")
pretty_json "$RESP"
echo
echo

echo "==== Q1 (LENTO) - Tentando entregar com ACKs incompletos (/deliver) ===="
RESP=$(curl -s -X POST "${BASE_URL}/deliver" \
  -H "Content-Type: application/json" \
  -d '{"process_id": 1}')
pretty_json "$RESP"
echo
echo ">> Esperado: status=waiting_acks, ainda faltam ACKs."
echo

echo "==== Q1 (LENTO) - Agora o processo 2 finalmente responde ACK (/ack) ===="
RESP=$(curl -s -X POST "${BASE_URL}/ack" \
  -H "Content-Type: application/json" \
  -d "{\"process_id\": 2, \"msg_id\": \"${MSG_ID}\"}")
pretty_json "$RESP"
echo
echo

echo "==== Q1 (LENTO) - Tentando entregar de novo (/deliver) ===="
RESP=$(curl -s -X POST "${BASE_URL}/deliver" \
  -H "Content-Type: application/json" \
  -d '{"process_id": 1}')
pretty_json "$RESP"
echo
echo

echo "==== Q1 (LENTO) - Estado final (/state) ===="
RESP=$(curl -s "${BASE_URL}/state")
pretty_json "$RESP"
echo
