#!/usr/bin/env bash
set -euo pipefail

# 1. Run terraform apply (interactive approval)
terraform apply

# 2. Save the private key from Terraform output into ~/.ssh
echo "[INFO] Writing private key to ~/.ssh/master-key.pem..."
terraform output -raw master_private_key_pem > ~/.ssh/master-key.pem
chmod 600 ~/.ssh/master-key.pem

# 3. Generate SSH config
echo "[INFO] Generating SSH config..."
./generate-ssh-config.sh

# 4. Copy files to the instances
echo "[INFO] Copying files to instances..."
./copy-files.sh

echo "[INFO] All done!"