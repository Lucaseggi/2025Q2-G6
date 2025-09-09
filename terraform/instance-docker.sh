#!/usr/bin/env bash
set -euo pipefail

SSH_CONFIG="$HOME/.ssh/terraform_config"

# Get IPs from terraform outputs
RABBITMQ_HOST=$(terraform output -raw queue_private_ip)
OPENSEARCH_IP=$(terraform output -raw vector_db_private_ip)
EMBEDDER_IP=$(terraform output -raw embedder_ms_private_ip)

ORDERED_INSTANCES=(
  "queue"
  "embedder-ms"
  "scraper-ms"
  "processor-ms"
  "vector-db"
  "inserter-ms"
  "bastion"
)
# Define docker build + run commands per host
declare -A COMMANDS=(
  # Queue (RabbitMQ)
  ["queue"]="
    docker build -t rabbitmq-image ./00-rabbitmq &&
    docker rm -f rabbitmq-server || true &&
    docker run -d \
      --name rabbitmq-server \
      --env-file ./00-rabbitmq/.env \
      -p 5672:5672 \
      -p 15672:15672 \
      -v rabbitmq-data:/var/lib/rabbitmq \
      -v rabbitmq-logs:/var/log/rabbitmq \
      rabbitmq-image
  "

  # Embedder
  ["embedder-ms"]="
    docker build -t embedder-image ./03-embedder &&
    docker rm -f embedder || true &&
    docker run -d \
      --name embedder \
      --env-file ./03-embedder/.env \
      -e RABBITMQ_HOST=$RABBITMQ_HOST \
      -p 8001:8001 \
      embedder-image
  "

  # Scraper
  ["scraper-ms"]="
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
  ["processor-ms"]="
    docker build -t processor-image ./02-processor &&
    docker rm -f processor || true &&
    docker run -d \
      --name processor \
      --env-file ./02-processor/.env \
      -e RABBITMQ_HOST=$RABBITMQ_HOST \
      processor-image
  "

  # OpenSearch (vector-db)
  ["vector-db"]="
    docker build -t opensearch-image ./opensearch-db &&
    docker rm -f opensearch-node || true &&
    docker run -d \
      --name opensearch-node \
      --env-file ./opensearch-db/.env \
      --ulimit memlock=-1:-1 \
      --ulimit nofile=65536:65536 \
      -p 9200:9200 \
      -p 9600:9600 \
      -v opensearch-data:/usr/share/opensearch/data \
      opensearch-image
  "

  # Inserter
  ["inserter-ms"]="
    docker build -t inserter-image ./04-inserter &&
    docker rm -f inserter || true &&
    docker run -d \
      --name inserter \
      --env-file ./04-inserter/.env \
      -e RABBITMQ_HOST=$RABBITMQ_HOST \
      -e OPENSEARCH_ENDPOINT=http://$OPENSEARCH_IP:9200 \
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