#!/usr/bin/env bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Get the script directory and terraform-lambda directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TF_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

log_info "=========================================="
log_info "Post-Terraform Deployment Script"
log_info "=========================================="
log_info "Script directory: $SCRIPT_DIR"
log_info "Terraform directory: $TF_DIR"
log_info "=========================================="
echo ""

# Change to terraform directory
cd "$TF_DIR"

# Verify terraform state exists
if [ ! -f "terraform.tfstate" ] || [ ! -s "terraform.tfstate" ]; then
    log_error "No Terraform state found. Have you run 'terraform apply' yet?"
    exit 1
fi

# 1. Save the private key from Terraform output into ~/.ssh
log_info "Step 1/4: Writing private key to ~/.ssh/master-key.pem..."

# Create .ssh directory if it doesn't exist and set proper permissions
mkdir -p ~/.ssh
chmod 700 ~/.ssh

terraform output -raw master_private_key_pem > ~/.ssh/master-key.pem
chmod 700 ~/.ssh/master-key.pem

log_info "✓ Private key saved"
echo ""

# 2. Generate SSH config
log_info "Step 2/4: Generating SSH config..."
"$SCRIPT_DIR/generate-ssh-config.sh"
echo ""

# 3. Copy files to the instances
log_info "Step 3/4: Copying files to instances..."
"$SCRIPT_DIR/copy-files.sh"
echo ""

# 4. Start docker instances
log_info "Step 4/4: Initializing docker instances..."
"$SCRIPT_DIR/instance-docker.sh"
echo ""

log_info "=========================================="
log_info "Post-Deployment Complete!"
log_info "=========================================="
log_info ""
log_info "Next Steps:"
log_info "1. Connect to bastion: ssh -F ~/.ssh/terraform_config bastion"
log_info "2. Connect to vector-db: ssh -F ~/.ssh/terraform_config vector-db"
log_info "3. Check OpenSearch: curl http://\$(terraform output -raw vector_db_private_ip):9200"
log_info "=========================================="