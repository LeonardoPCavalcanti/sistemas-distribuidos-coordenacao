#!/usr/bin/env bash
set -euo pipefail

IMAGE="algoritmos-distribuidos:latest"

STS_NAME="algoritmos-coordenacao"
POD_PREFIX="algoritmos-coordenacao"

echo "==> Indo para a pasta do projeto (onde está este script)..."
cd "$(dirname "$0")"

command -v minikube >/dev/null 2>&1 || { echo "ERRO: minikube não encontrado."; exit 1; }
command -v kubectl  >/dev/null 2>&1 || { echo "ERRO: kubectl não encontrado."; exit 1; }
command -v docker   >/dev/null 2>&1 || { echo "ERRO: docker não encontrado."; exit 1; }

echo "==> Subindo Minikube (Cloud Shell: 2 CPUs)..."
minikube status >/dev/null 2>&1 && minikube stop >/dev/null 2>&1 || true
minikube delete >/dev/null 2>&1 || true
minikube start --cpus=2 --memory=4096

echo "==> Configurando Docker para usar o daemon do Minikube..."
eval "$(minikube docker-env)"

echo "==> Build da imagem Docker: ${IMAGE}"
docker build -t "${IMAGE}" .

echo "==> Aplicando manifestos Kubernetes..."
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/statefulset.yaml

echo "==> Aguardando pods ficarem prontos..."
kubectl rollout status statefulset/"${STS_NAME}" --timeout=180s || true
for p in 0 1 2; do
  echo "   - aguardando readiness do ${POD_PREFIX}-$p..."
  kubectl wait --for=condition=Ready pod/"${POD_PREFIX}-$p" --timeout=180s
done

echo "==> (Re)iniciando port-forwards..."
pkill -f "kubectl port-forward pod/${POD_PREFIX}-0 8080:8080" >/dev/null 2>&1 || true
pkill -f "kubectl port-forward pod/${POD_PREFIX}-1 8081:8080" >/dev/null 2>&1 || true
pkill -f "kubectl port-forward pod/${POD_PREFIX}-2 8082:8080" >/dev/null 2>&1 || true

nohup kubectl port-forward pod/"${POD_PREFIX}-0" 8080:8080 >/dev/null 2>&1 &
nohup kubectl port-forward pod/"${POD_PREFIX}-1" 8081:8080 >/dev/null 2>&1 &
nohup kubectl port-forward pod/"${POD_PREFIX}-2" 8082:8080 >/dev/null 2>&1 &

sleep 2

echo ""
echo "✅ Ambiente pronto! Pods em Running e port-forwards configurados:"
echo "   - P0 -> http://127.0.0.1:8080"
echo "   - P1 -> http://127.0.0.1:8081"
echo "   - P2 -> http://127.0.0.1:8082"
echo ""
echo "=============================================================="
echo "AGORA ABRA 3 TERMINAIS (Cloud Shell: 'Open in new tab') E RODE:"
echo "=============================================================="
echo ""
echo "Terminal 1 (logs P0):"
echo "kubectl logs -f ${POD_PREFIX}-0"
echo ""
echo "Terminal 2 (logs P1):"
echo "kubectl logs -f ${POD_PREFIX}-1"
echo ""
echo "Terminal 3 (logs P2):"
echo "kubectl logs -f ${POD_PREFIX}-2"
echo ""
echo "=============================================================="
echo "No terminal principal, rode os testes:"
echo "cd testes"
echo "./teste_q1_normal.sh"
echo "./teste_q1_lento.sh"
echo "./teste_q2.sh"
echo "./teste_q3.sh"
echo "=============================================================="
echo ""
