#!/usr/bin/env bash
set -euo pipefail

SSH_CONFIG="$HOME/.ssh/terraform_config"

# Map of local folders to instance hostnames
declare -A FOLDERS=(
  ["scrapper-ms"]="../01-scraper-ms"
  ["processing-ms"]="../02-processing-ms"
  ["embedding-ms"]="../03-embedding-ms"
  ["inserter-ms"]="../04-inserter-ms"
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
