#!/usr/bin/env bash
set -euo pipefail

SSH_CONFIG="$HOME/.ssh/terraform_config"

# Map of local folders to instance hostnames
declare -A FOLDERS=(
  # ["bastion"]="../api"
  ["vector-db"]="../07-vectorial-db"
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
