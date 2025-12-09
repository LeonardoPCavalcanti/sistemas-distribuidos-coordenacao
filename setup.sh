#!/usr/bin/env bash
set -euo pipefail

# ============================
#  Configurações principais
# ============================
PROJ_DIR="$HOME/av2"
PROFILE_NAME="k8s-2n"
IMAGE_NAME="priority-api:v5"
DEPLOY_FILE="api-deployment.yaml"

echo "📁 Indo para a pasta do projeto: $PROJ_DIR"
cd "$PROJ_DIR"

echo
echo "🚀 Iniciando/reativando o cluster Minikube (profile: $PROFILE_NAME)..."

# Verifica se o profile já existe
if minikube profile list 2>/dev/null | grep -q "^$PROFILE_NAME"; then
  echo "▶️  Profile $PROFILE_NAME já existe, apenas iniciando..."
  minikube start -p "$PROFILE_NAME"
else
  echo "🆕 Criando profile $PROFILE_NAME com 2 nós..."
  minikube start -p "$PROFILE_NAME" --nodes=2
fi

echo
echo "🧭 Configurando contexto do kubectl para usar o cluster $PROFILE_NAME..."
kubectl config use-context "$PROFILE_NAME"

echo
echo "🧹 Limpando recursos antigos (service e deployment)..."
kubectl delete service priority-api-svc --ignore-not-found
kubectl delete deployment priority-api --ignore-not-found

echo
echo "🐳 Fazendo build da imagem Docker $IMAGE_NAME..."
docker build -t "$IMAGE_NAME" .

echo
echo "📦 Enviando imagem para o cluster Minikube (profile: $PROFILE_NAME)..."
minikube image load "$IMAGE_NAME" -p "$PROFILE_NAME"

echo
echo "📜 Aplicando Deployment e Service a partir de $DEPLOY_FILE..."
kubectl apply -f "$DEPLOY_FILE"

echo
echo "⏳ Aguardando rollout do deployment priority-api..."
kubectl rollout status deployment priority-api

echo
echo "📡 Pods atuais no cluster:"
kubectl get pods -o wide

echo
echo "✅ Ambiente pronto!"
echo
echo "👉 Em OUTRO terminal, faça o port-forward para testar a API:"
echo "   cd ~/av2"
echo "   kubectl port-forward pod/$(kubectl get pod -l app=priority-api -o jsonpath="{.items[0].metadata.name}") 8080:8080"
echo "   kubectl port-forward pod/$(kubectl get pod -l app=priority-api -o jsonpath="{.items[1].metadata.name}") 8080:8080"
echo "   kubectl port-forward pod/$(kubectl get pod -l app=priority-api -o jsonpath="{.items[2].metadata.name}") 8080:8080"
echo
echo "👉 Depois rode os testes:"
echo "   ./teste_q1_normal.sh"
echo "   ./teste_q1_lento.sh"
echo "   ./teste_q2.sh"
echo "   ./teste_q3.sh"