#!/usr/bin/env bash
set -euo pipefail

# 1. Run terraform apply (interactive approval)
# terraform apply

# 2. Save the private key from Terraform output into ~/.ssh
echo "[INFO] Writing private key to ~/.ssh/master-key.pem..."
terraform output -raw master_private_key_pem | tee ~/.ssh/master-key.pem > /dev/null
chmod 400 ~/.ssh/master-key.pem

# 3. Generate SSH config
echo "[INFO] Generating SSH config..."
./ec2-scripts/generate-ssh-config.sh

# 4. Copy files to the instances
echo "[INFO] Copying files to instances..."
./ec2-scripts/copy-files.sh

# 5. Start docker instances
echo "[INFO] Initializing docker instances..."
./ec2-scripts/instance-docker.sh

echo "[INFO] All done!"