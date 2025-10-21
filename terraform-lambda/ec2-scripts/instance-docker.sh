#!/usr/bin/env bash
set -euo pipefail

# Get the script directory and terraform-lambda directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TF_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to terraform directory to run terraform commands
cd "$TF_DIR"

SSH_CONFIG="$HOME/.ssh/terraform_config"

# Get IPs from terraform outputs
OPENSEARCH_IP=$(terraform output -raw vector_db_private_ip)

ORDERED_INSTANCES=(
  "vector-db"
  # "bastion"
)
# Define docker build + run commands per host
declare -A COMMANDS=(
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
)

# Deploy to each instance
for instance in "${ORDERED_INSTANCES[@]}"; do
  echo "🚀 Deploying containers on $instance ..."
  ssh -F "$SSH_CONFIG" "$instance" "cd /home/ec2-user && ${COMMANDS[$instance]}"
done

echo "✅ All containers deployed."