#!/usr/bin/env bash
set -euo pipefail

# Path to the Terraform SSH config
SSH_CONFIG="$HOME/.ssh/terraform_config"

# Backup existing terraform_config if it exists
if [[ -f "$SSH_CONFIG" ]]; then
    cp "$SSH_CONFIG" "$SSH_CONFIG.bak.$(date +%s)"
fi

# Start with a fresh file
echo "" > "$SSH_CONFIG"

# Terraform outputs
BASTION_IP=$(terraform output -raw api_rest_public_ip)
BASTION_USER="ec2-user"
BASTION_KEY="~/.ssh/master-key.pem"

# Write bastion host entry
{
  echo "Host bastion"
  echo "    HostName $BASTION_IP"
  echo "    User $BASTION_USER"
  echo "    IdentityFile $BASTION_KEY"
  echo
} >> "$SSH_CONFIG"

# List of instance hostnames
INSTANCES=("scrapper-ms" "processing-ms" "embedding-ms" "inserter-ms")

# Loop through instances to generate config
for instance in "${INSTANCES[@]}"; do
  TF_KEY="${instance//-/_}_private_ip"
  IP=$(terraform output -raw "$TF_KEY")
  
  if [[ -n "$IP" ]]; then
    {
      echo "Host $instance"
      echo "    HostName $IP"
      echo "    User ec2-user"
      echo "    IdentityFile $BASTION_KEY"
      echo "    ProxyJump bastion"
      echo
    } >> "$SSH_CONFIG"
  fi
done

echo "✅ SSH config created at $SSH_CONFIG."
echo "Use it with: ssh -F $SSH_CONFIG <host>"
