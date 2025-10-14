#!/usr/bin/env bash
set -euo pipefail

SSH_CONFIG="$HOME/.ssh/terraform_config"

# Get IPs from terraform outputs
RABBITMQ_HOST=$(terraform output -raw queue_private_ip)
OPENSEARCH_IP=$(terraform output -raw vector_db_private_ip)
POSTGRES_HOST=$(terraform output -raw relational_db_private_ip)
EMBEDDER_IP=$(terraform output -raw embedder_private_ip)
RELATIONAL_GUARD_IP=$(terraform output -raw relational_guard_private_ip)
VECTORIAL_GUARD_IP=$(terraform output -raw vectorial_guard_private_ip)

ORDERED_INSTANCES=(
  "queue"
  "vector-db"
  "relational-db"
  "embedder"
  "scraper"
  "processor"
  "relational-guard"
  "vectorial-guard"
  "inserter"
  # "bastion"
)
# Define docker build + run commands per host
declare -A COMMANDS=(
  # Queue (RabbitMQ)
  ["queue"]="
    docker build -t rabbitmq-image ./00-queue &&
    docker rm -f rabbitmq-server || true &&
    docker run -d \
      --name rabbitmq-server \
      --env-file ./00-queue/.env \
      -p 5672:5672 \
      -p 15672:15672 \
      -v rabbitmq-data:/var/lib/rabbitmq \
      -v rabbitmq-logs:/var/log/rabbitmq \
      rabbitmq-image
  "
  # OpenSearch (vector-db)
  ["vector-db"]="
    docker build -t opensearch-image ./07-vectorial-db &&
    docker rm -f opensearch-node || true &&
    docker run -d \
      --name opensearch-node \
      --env-file ./07-vectorial-db/.env \
      --ulimit memlock=-1:-1 \
      --ulimit nofile=65536:65536 \
      -p 9200:9200 \
      -p 9600:9600 \
      -v opensearch-data:/usr/share/opensearch/data \
      opensearch-image
  "

  # PostgreSQL (relational-db)
  ["relational-db"]="
    docker build -t postgres-image ./06-relational-db &&
    docker rm -f postgres-db || true &&
    docker run -d \
      --name postgres-db \
      -e POSTGRES_DB=simpla_rag \
      -e POSTGRES_USER=postgres \
      -e POSTGRES_PASSWORD=postgres123 \
      -p 5432:5432 \
      -v postgres-data:/var/lib/postgresql/data/pgdata \
      postgres-image
  "

  # Embedder
  ["embedder"]="
    docker build -t embedder-image ./04-embedder &&
    docker rm -f embedder || true &&
    docker run -d \
      --name embedder \
      --env-file ./04-embedder/.env \
      -e RABBITMQ_HOST=$RABBITMQ_HOST \
      -p 8001:8001 \
      embedder-image
  "

  # Scraper
  ["scraper"]="
    docker build -t scraper-image ./01-scraper &&
    docker rm -f scraper || true &&
    docker run -d \
      --name scraper \
      --env-file ./01-scraper/.env \
      -e RABBITMQ_HOST=$RABBITMQ_HOST \
      -p 8003:8003 \
      scraper-image
  "

  # Processor
  ["processor"]="
    docker build -t processor-image ./03-processor &&
    docker rm -f processor || true &&
    docker run -d \
      --name processor \
      --env-file ./03-processor/.env \
      -e RABBITMQ_HOST=$RABBITMQ_HOST \
      processor-image
  "

  # Relational Guard
  ["relational-guard"]="
    docker build -t relational-guard-image ./06-relational-guard &&
    docker rm -f relational-guard || true &&
    docker run -d \
      --name relational-guard \
      --env-file ./06-relational-guard/.env \
      -e POSTGRES_HOST=$POSTGRES_HOST \
      -e POSTGRES_PORT=5432 \
      -e POSTGRES_DB=simpla_rag \
      -e POSTGRES_USER=postgres \
      -e POSTGRES_PASSWORD=postgres123 \
      -p 50051:50051 \
      relational-guard-image
  "

  # Vectorial Guard
  ["vectorial-guard"]="
    docker build -t vectorial-guard-image ./07-vectorial-guard &&
    docker rm -f vectorial-guard || true &&
    docker run -d \
      --name vectorial-guard \
      --env-file ./07-vectorial-guard/.env \
      -e OPENSEARCH_ENDPOINT=http://$OPENSEARCH_IP:9200 \
      -p 50052:50052 \
      vectorial-guard-image
  "

  # Inserter
  ["inserter"]="
    sleep 20
    docker build -t inserter-image ./05-inserter &&
    docker rm -f inserter || true &&
    docker run -d \
      --name inserter \
      --env-file ./05-inserter/.env \
      -e RABBITMQ_HOST=$RABBITMQ_HOST \
      -e OPENSEARCH_ENDPOINT=http://$OPENSEARCH_IP:9200 \
      -e RELATIONAL_GUARD_HOST=$RELATIONAL_GUARD_IP:50051 \
      -e VECTORIAL_GUARD_HOST=$VECTORIAL_GUARD_IP:50052 \
      inserter-image
  "

  # API (bastion)
  ["bastion"]="
    docker build -t api-image ./api &&
    docker rm -f api || true &&
    docker run -d \
      --name api \
      --env-file ./api/.env \
      -e OPENSEARCH_ENDPOINT=http://$OPENSEARCH_IP:9200 \
      -e EMBEDDING_SERVICE_URL=http://$EMBEDDER_IP:8001 \
      -p 8000:8000 \
      api-image
  "
)

# Deploy to each instance
for instance in "${ORDERED_INSTANCES[@]}"; do
  echo "🚀 Deploying containers on $instance ..."
  ssh -F "$SSH_CONFIG" "$instance" "cd /home/ec2-user && ${COMMANDS[$instance]}"
done

echo "✅ All containers deployed."