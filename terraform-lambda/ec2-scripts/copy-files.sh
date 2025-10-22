#!/usr/bin/env bash
set -euo pipefail

# Get the script directory and terraform-lambda directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TF_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to terraform directory
cd "$TF_DIR"

SSH_CONFIG="$HOME/.ssh/terraform_config"

# Map of local folders to instance hostnames (relative to simpla_cloud directory)
declare -A FOLDERS=(
  # ["bastion"]="api"
  ["vector-db"]="07-vectorial-db"
)

# Loop through instances to copy folders
for instance in "${!FOLDERS[@]}"; do
  FOLDER_NAME="${FOLDERS[$instance]}"
  # Path relative to simpla_cloud (parent of terraform-lambda)
  LOCAL_FOLDER="$TF_DIR/../$FOLDER_NAME"

  if [[ -d "$LOCAL_FOLDER" ]]; then
    echo "Copying $LOCAL_FOLDER to $instance:/home/ec2-user/"
    scp -F "$SSH_CONFIG" -r "$LOCAL_FOLDER" "$instance:/home/ec2-user/"
  else
    echo "Warning: folder $LOCAL_FOLDER does not exist (expected at $LOCAL_FOLDER)"
  fi
done

echo "✅ Files copied to all instances."
