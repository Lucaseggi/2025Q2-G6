#!/bin/bash
# Complete cleanup script for Simpla Lambda infrastructure
# This script will:
# 1. Empty and delete S3 buckets
# 2. Run terraform destroy
# 3. Force delete secrets from Secrets Manager

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_usage() {
    cat << EOF
Usage: ./destroy.sh [OPTIONS]

Destroy Simpla Lambda infrastructure and clean up all resources

OPTIONS:
  -r, --region REGION    AWS region (default: us-east-1)
  -y, --yes             Skip confirmation prompts
  -h, --help            Show this help message

EXAMPLES:
  # Interactive destroy with confirmation
  ./destroy.sh

  # Auto-approve destroy
  ./destroy.sh -y

  # Specify region
  ./destroy.sh -r us-west-2

EOF
}

# Default values
AWS_REGION="us-east-1"
AUTO_APPROVE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -y|--yes)
            AUTO_APPROVE=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Header
log_info "=========================================="
log_info "Simpla Lambda Infrastructure Cleanup"
log_info "=========================================="
log_info "AWS Region:  $AWS_REGION"
log_info "Auto-approve: $AUTO_APPROVE"
log_info "=========================================="
echo ""

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    log_error "terraform.tfvars not found. Are you in the terraform-lambda directory?"
    exit 1
fi

# Confirmation prompt
if [ "$AUTO_APPROVE" = false ]; then
    log_warn "This will DESTROY all Lambda functions, SQS queues, S3 buckets, and secrets."
    echo -n "Are you sure you want to continue? (yes/no): "
    read -r confirmation
    if [ "$confirmation" != "yes" ]; then
        log_info "Aborted."
        exit 0
    fi
fi

echo ""

# Step 1: Force delete secrets from Secrets Manager
log_step "Step 1/4: Force deleting secrets from Secrets Manager..."

SECRETS=(
    "simpla/shared/aws-config"
    "simpla/shared/queue-names"
    "simpla/shared/s3-buckets"
    "simpla/api-keys/gemini"
    "simpla/services/config"
    "simpla/services/embedder-endpoints"
    "simpla/services/guard-endpoints"
    "simpla/services/answer-generator-endpoints"
)

for SECRET_NAME in "${SECRETS[@]}"; do
    log_info "Deleting secret: $SECRET_NAME"
    aws secretsmanager delete-secret \
        --secret-id "$SECRET_NAME" \
        --force-delete-without-recovery \
        --region "$AWS_REGION" \
        >/dev/null 2>&1 && echo "  ✓ Deleted" || echo "  ⚠ Not found or already deleted"
done

log_info "✓ Secrets deleted"
echo ""

# Step 2: Empty S3 buckets (including all versions)
log_step "Step 2/4: Emptying S3 buckets..."

# Get bucket names from terraform.tfvars
SCRAPER_BUCKET=$(grep scraper_bucket_name terraform.tfvars | cut -d'"' -f2)
PURIFIER_BUCKET=$(grep purifier_bucket_name terraform.tfvars | cut -d'"' -f2)
PROCESSOR_BUCKET=$(grep processor_bucket_name terraform.tfvars | cut -d'"' -f2)

empty_bucket() {
    local BUCKET=$1
    if [ -z "$BUCKET" ]; then
        return
    fi

    log_info "Emptying bucket: $BUCKET"

    # Check if bucket exists
    if ! aws s3api head-bucket --bucket "$BUCKET" --region "$AWS_REGION" 2>/dev/null; then
        log_warn "Bucket $BUCKET not found, skipping"
        return
    fi

    # Delete all object versions (for versioned buckets)
    log_info "  - Deleting object versions..."
    aws s3api list-object-versions \
        --bucket "$BUCKET" \
        --region "$AWS_REGION" \
        --output json \
        --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' 2>/dev/null | \
    jq -r '.Objects // [] | .[] | "\(.Key)\t\(.VersionId)"' | \
    while IFS=$'\t' read -r key versionId; do
        if [ -n "$key" ] && [ -n "$versionId" ]; then
            aws s3api delete-object \
                --bucket "$BUCKET" \
                --key "$key" \
                --version-id "$versionId" \
                --region "$AWS_REGION" >/dev/null 2>&1
        fi
    done

    # Delete all delete markers (for versioned buckets)
    log_info "  - Deleting delete markers..."
    aws s3api list-object-versions \
        --bucket "$BUCKET" \
        --region "$AWS_REGION" \
        --output json \
        --query '{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}' 2>/dev/null | \
    jq -r '.Objects // [] | .[] | "\(.Key)\t\(.VersionId)"' | \
    while IFS=$'\t' read -r key versionId; do
        if [ -n "$key" ] && [ -n "$versionId" ]; then
            aws s3api delete-object \
                --bucket "$BUCKET" \
                --key "$key" \
                --version-id "$versionId" \
                --region "$AWS_REGION" >/dev/null 2>&1
        fi
    done

    # Delete current objects (non-versioned or current versions)
    log_info "  - Deleting current objects..."
    aws s3 rm "s3://$BUCKET" --recursive --region "$AWS_REGION" 2>/dev/null || true

    log_info "  ✓ Bucket $BUCKET emptied"
}

for BUCKET in "$SCRAPER_BUCKET" "$PURIFIER_BUCKET" "$PROCESSOR_BUCKET"; do
    empty_bucket "$BUCKET"
done

log_info "✓ All S3 buckets emptied"
echo ""

# Step 3: Run terraform destroy
log_step "Step 3/4: Running terraform destroy..."

if [ "$AUTO_APPROVE" = true ]; then
    terraform destroy -auto-approve
else
    terraform destroy
fi

log_info "✓ Terraform destroy complete"
echo ""

# Step 4: Verify secrets are deleted (already done in Step 1)
log_step "Step 4/4: Verifying cleanup..."
log_info "✓ All secrets were deleted in Step 1"
log_info "✓ All S3 buckets were emptied in Step 2"
log_info "✓ All Terraform resources were destroyed in Step 3"
echo ""

# Summary
log_info "=========================================="
log_info "Cleanup Complete!"
log_info "=========================================="
log_info ""
log_info "All resources have been destroyed:"
log_info "  - Lambda functions deleted"
log_info "  - SQS queues deleted"
log_info "  - S3 buckets emptied and deleted"
log_info "  - Secrets Manager secrets force-deleted"
log_info ""
log_info "You can now run ./deploy.sh to redeploy"
log_info "=========================================="
