#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:8080}

pretty_json() {
  local body="$1"
  echo "$body" | python -m json.tool 2>/dev/null || echo "$body"
}

echo "==== Q3 - Estado inicial do Bully (/bully/state) ===="
RESP=$(curl -s "${BASE_URL}/bully/state")
pretty_json "$RESP"
echo
echo

echo "==== Q3 - Coordenador atual (/bully/coordinator) ===="
RESP=$(curl -s "${BASE_URL}/bully/coordinator")
pretty_json "$RESP"
echo
echo

echo "==== Q3 - Simulando falha do coordenador (proc 3) (/bully/fail) ===="
RESP=$(curl -s -X POST "${BASE_URL}/bully/fail" \
  -H "Content-Type: application/json" \
  -d '{"process_id": 3}')
pretty_json "$RESP"
echo
echo

echo "==== Q3 - Estado após falha de 3 (/bully/state) ===="
RESP=$(curl -s "${BASE_URL}/bully/state")
pretty_json "$RESP"
echo
echo

echo "==== Q3 - Processo 1 inicia eleição (/bully/election) ===="
RESP=$(curl -s -X POST "${BASE_URL}/bully/election" \
  -H "Content-Type: application/json" \
  -d '{"process_id": 1}')
pretty_json "$RESP"
echo
echo

echo "==== Q3 - Estado após eleição iniciada por 1 (/bully/state) ===="
RESP=$(curl -s "${BASE_URL}/bully/state")
pretty_json "$RESP"
echo
echo

echo "==== Q3 - Recuperando processo 3 (/bully/recover) ===="
RESP=$(curl -s -X POST "${BASE_URL}/bully/recover" \
  -H "Content-Type: application/json" \
  -d '{"process_id": 3}')
pretty_json "$RESP"
echo
echo

echo "==== Q3 - Processo 1 inicia nova eleição (3 vivo) (/bully/election) ===="
RESP=$(curl -s -X POST "${BASE_URL}/bully/election" \
  -H "Content-Type: application/json" \
  -d '{"process_id": 1}')
pretty_json "$RESP"
echo
echo

echo "==== Q3 - Estado final do Bully (/bully/state) ===="
RESP=$(curl -s "${BASE_URL}/bully/state")
pretty_json "$RESP"
echo
