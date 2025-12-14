#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "  TESTE Q3 - ELEIÇÃO DE LÍDER (BULLY)"
echo "=========================================="
echo ""
echo "Legenda (nomes mais claros):"
echo "  Nó 0 = algoritmos-coordenacao-0 (iniciador do teste)"
echo "  Nó 1 = algoritmos-coordenacao-1"
echo "  Nó 2 = algoritmos-coordenacao-2 (maior ID, tende a virar líder)"
echo ""
echo "Eventos:"
echo "  ELEICAO      = mensagem ELECTION (início/propagação)"
echo "  RESPOSTA     = mensagem ANSWER (confirma que existe nó com ID maior)"
echo "  LIDER        = mensagem COORDINATOR (líder anunciado)"
echo ""

strip_ansi() { sed -r 's/\x1B\[[0-9;]*[mK]//g'; }

cleanup() {
  echo ""
  echo "Encerrando port-forwards..."
  kill "${PF0:-0}" "${PF1:-0}" "${PF2:-0}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Renomeia termos no output (só para ficar didático)
pretty_labels() {
  sed -E \
    -e 's/Processo-0/Nó-0/g' \
    -e 's/Processo-1/Nó-1/g' \
    -e 's/Processo-2/Nó-2/g' \
    -e 's/\bELECTION\b/ELEICAO/g' \
    -e 's/\bANSWER\b/RESPOSTA/g' \
    -e 's/\bCOORDINATOR\b/LIDER/g' \
    -e 's/ledder/lider/g' \
    -e 's/Ledder/Lider/g'
}

extract_election_logs() {
  local pod="$1"
  local title="$2"

  echo ""
  echo "------------------------------------------"
  echo "${title}"
  echo "------------------------------------------"

  # Pega logs recentes e filtra só o que interessa para a eleição
  kubectl logs "$pod" --since=10m 2>/dev/null \
    | strip_ansi \
    | pretty_labels \
    | grep -a -E "INICIANDO|Recebido|Enviando|ELEICAO|RESPOSTA|LIDER|Falha ao enviar" \
    | sed 's/^/  /' \
    || echo "  (Nenhum log de eleição encontrado)"
}

echo "Verificando pods..."
kubectl get pods | grep -E "algoritmos-coordenacao-(0|1|2)" || true
echo ""

echo "Configurando port-forwards..."
kubectl port-forward pods/algoritmos-coordenacao-0 8080:8080 >/dev/null 2>&1 & PF0=$!
kubectl port-forward pods/algoritmos-coordenacao-1 8081:8080 >/dev/null 2>&1 & PF1=$!
kubectl port-forward pods/algoritmos-coordenacao-2 8082:8080 >/dev/null 2>&1 & PF2=$!

sleep 2
echo ""

echo "=========================================="
echo "Ação do teste: Nó 0 inicia a eleição"
echo "=========================================="
curl -s -X POST "http://127.0.0.1:8080/start-election" >/dev/null
sleep 6

extract_election_logs "algoritmos-coordenacao-0" "Nó 0 (Iniciador) - decisões e respostas recebidas"
extract_election_logs "algoritmos-coordenacao-1" "Nó 1 - reage ao Nó 0 e tenta subir eleição"
extract_election_logs "algoritmos-coordenacao-2" "Nó 2 (Maior ID) - tende a se declarar líder"

echo ""
echo "=========================================="
echo "Resumo rápido: líder anunciado nos logs"
echo "=========================================="
for pod in algoritmos-coordenacao-0 algoritmos-coordenacao-1 algoritmos-coordenacao-2; do
  kubectl logs "$pod" --since=10m 2>/dev/null \
    | strip_ansi \
    | pretty_labels \
    | grep -a -E "LIDER" \
    | tail -n 2 \
    | sed "s/^/  [$pod] /" \
    || true
done

echo ""
echo "Teste Q3 finalizado!"
