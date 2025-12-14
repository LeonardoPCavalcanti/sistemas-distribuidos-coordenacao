# Algoritmos de Coordenação Distribuída

Este repositório contém uma implementação prática de **algoritmos clássicos de coordenação em sistemas distribuídos**, utilizando **FastAPI**, **Docker** e **Kubernetes (Minikube)**.

Cada processo do sistema é executado em um *pod* independente e se comunica via HTTP, permitindo observar concorrência, ordenação e coordenação em um ambiente distribuído real.

---

## Algoritmos Implementados

- **Q1 – Multicast Ordenado**
- **Q2 – Exclusão Mútua Distribuída**
- **Q3 – Eleição de Líder (Bully)**

---

## Arquitetura do Sistema

### Infraestrutura
- **Orquestração**: Kubernetes (Minikube)
- **Containers**: Docker
- **Backend**: FastAPI (Python 3.9)
- **Processos**: 3 pods em StatefulSet  
  - `algoritmos-coordenacao-0`
  - `algoritmos-coordenacao-1`
  - `algoritmos-coordenacao-2`
- **Descoberta de serviços**: Service headless (DNS interno do Kubernetes)
- **Comunicação**: HTTP entre pods

---

## Estrutura do Projeto

```text
algoritmos-coordenacao/
│
├── k8s/
│   ├── service.yaml
│   └── statefulset.yaml
│
├── src/
│   ├── routes/
│   │   ├── q1_multicast.py
│   │   ├── q2_mutex.py
│   │   └── q3_election.py
│   │
│   ├── __init__.py
│   ├── algorithms.py
│   ├── config.py
│   ├── http_client.py
│   ├── logging_config.py
│   ├── main.py
│   └── schemas.py
│
├── testes/
│   ├── teste_q1_normal.sh
│   ├── teste_q1_lento.sh
│   ├── teste_q2.sh
│   └── teste_q3.sh
│
├── Dockerfile
├── requirements.txt
├── setup.sh
└── README.md
```

---

## Q1 – Multicast Ordenado

Implementa um mecanismo de **envio de mensagens para todos os processos**, garantindo que **todas sejam processadas na mesma ordem**, mesmo com atrasos.

### Funcionamento geral
- Cada processo mantém um **relógio lógico**
- Mensagens recebidas são armazenadas em uma fila ordenada
- Um ACK é enviado para cada mensagem recebida
- Uma mensagem só é processada após o recebimento de ACKs de todos os processos

### Endpoints principais
- `POST /send`
- `POST /message`
- `POST /ack`

### Testes
```bash
./teste_q1_normal.sh
./teste_q1_lento.sh
```

---

## Q2 – Exclusão Mútua Distribuída

Implementa um protocolo de **controle de acesso a recurso compartilhado**, garantindo que apenas um processo entre na região crítica por vez.

### Funcionamento geral
- Processos solicitam acesso enviando pedidos com timestamp
- Respostas podem ser imediatas ou adiadas
- O processo entra na região crítica apenas após receber todas as permissões
- Ao sair, libera pedidos adiados

### Endpoints principais
- `POST /request-resource`
- `POST /receive-request`
- `POST /receive-reply`

### Teste
```bash
./teste_q2.sh
```

---

## Q3 – Eleição de Líder (Bully)

Implementa o **Algoritmo de Bully** para escolha de um líder entre os processos ativos.

### Funcionamento geral
- Um processo inicia a eleição enviando mensagens para IDs maiores
- Processos com ID maior respondem e iniciam nova eleição
- O processo com maior ID ativo se torna líder
- O líder notifica os demais com uma mensagem de coordenação

### Endpoints principais
- `POST /start-election`
- `POST /receive-election`
- `POST /receive-answer`
- `POST /receive-coordinator`

### Teste
```bash
./teste_q3.sh
```

---

## Execução do Projeto

### Pré-requisitos

```bash
docker --version
kubectl version --client
minikube version
```

---

### Setup Automático

Na raiz do projeto:

```bash
chmod +x setup.sh
./setup.sh
```

Portas locais:
- P0 → `http://127.0.0.1:8080`
- P1 → `http://127.0.0.1:8081`
- P2 → `http://127.0.0.1:8082`

---

## Acompanhando Logs

```bash
kubectl logs -f algoritmos-coordenacao-0
kubectl logs -f algoritmos-coordenacao-1
kubectl logs -f algoritmos-coordenacao-2
```

---

## Execução dos Testes

```bash
cd testes

./teste_q1_normal.sh
./teste_q1_lento.sh
./teste_q2.sh
./teste_q3.sh
```

---

## Limpeza do Ambiente

```bash
kubectl delete -f k8s/statefulset.yaml
kubectl delete -f k8s/service.yaml
minikube stop
```
