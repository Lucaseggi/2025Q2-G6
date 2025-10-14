#!/usr/bin/env bash
set -euo pipefail

SSH_CONFIG="$HOME/.ssh/terraform_config"

# Map of local folders to instance hostnames
declare -A FOLDERS=(
  # ["bastion"]="../api"
  ["vector-db"]="../06-vectorial-db"
  ["relational-db"]="../07-relational-db"
  ["queue"]="../00-queue"
  ["scraper"]="../01-scraper"
  ["processor"]="../03-processor"
  ["embedder"]="../04-embedder"
  ["inserter"]="../05-inserter"
  ["relational-guard"]="../06-relational-guard"
  ["vectorial-guard"]="../07-vectorial-guard"
)

# Loop through instances to copy folders
for instance in "${!FOLDERS[@]}"; do
  LOCAL_FOLDER="${FOLDERS[$instance]}"
  if [[ -d "$LOCAL_FOLDER" ]]; then
    echo "Copying $LOCAL_FOLDER to $instance:/home/ec2-user/"
    scp -F "$SSH_CONFIG" -r "$LOCAL_FOLDER" "$instance:/home/ec2-user/"
  else
    echo "Warning: folder $LOCAL_FOLDER does not exist"
  fi
done

echo "✅ Files copied to all instances."
