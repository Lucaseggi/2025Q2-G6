#!/bin/bash
set -e

# Simpla Lambda Deployment Script
# Orchestrates the full deployment: ECR push → Terraform apply

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
Usage: ./deploy.sh [OPTIONS]

Deploy Simpla microservices to AWS Lambda

OPTIONS:
  -a, --account ACCOUNT_ID   AWS account ID (required)
  -r, --region REGION        AWS region (default: us-east-1)
  -t, --tag TAG             Image tag (default: latest)
  --skip-ecr                Skip ECR deployment
  --skip-terraform          Skip Terraform apply
  -h, --help                Show this help message

EXAMPLES:
  # Full deployment (ECR + Terraform)
  ./deploy.sh -a 123456789012

  # Only deploy to ECR
  ./deploy.sh -a 123456789012 --skip-terraform

  # Only run Terraform (assumes images already in ECR)
  ./deploy.sh -a 123456789012 --skip-ecr

PREREQUISITES:
  1. AWS CLI configured
  2. Docker installed
  3. Terraform installed
  4. ECR repositories created
  5. terraform.tfvars configured

EOF
}

# Default values
AWS_REGION="us-east-1"
IMAGE_TAG="latest"
SKIP_ECR=false
SKIP_TERRAFORM=false
AWS_ACCOUNT_ID=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--account)
            AWS_ACCOUNT_ID="$2"
            shift 2
            ;;
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --skip-ecr)
            SKIP_ECR=true
            shift
            ;;
        --skip-terraform)
            SKIP_TERRAFORM=true
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

# Validate required parameters
if [ -z "$AWS_ACCOUNT_ID" ]; then
    log_error "AWS_ACCOUNT_ID is required"
    echo ""
    print_usage
    exit 1
fi

# Header
log_info "=========================================="
log_info "Simpla Lambda Deployment"
log_info "=========================================="
log_info "AWS Account:  $AWS_ACCOUNT_ID"
log_info "AWS Region:   $AWS_REGION"
log_info "Image Tag:    $IMAGE_TAG"
log_info "Skip ECR:     $SKIP_ECR"
log_info "Skip TF:      $SKIP_TERRAFORM"
log_info "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "terraform.tfvars" ]; then
    log_error "terraform.tfvars not found. Are you in the terraform-lambda directory?"
    exit 1
fi

# Step 1: Deploy to ECR
if [ "$SKIP_ECR" = false ]; then
    log_step "Step 1/2: Deploying Docker images to ECR..."

    if [ ! -f "../deploy-to-ecr.sh" ]; then
        log_error "deploy-to-ecr.sh not found in parent directory"
        exit 1
    fi

    cd ..
    ./deploy-to-ecr.sh -a "$AWS_ACCOUNT_ID" -r "$AWS_REGION" -t "$IMAGE_TAG" all
    cd terraform-lambda

    log_info "✓ ECR deployment complete"
    echo ""
else
    log_step "Step 1/2: Skipping ECR deployment"
    echo ""
fi

# Step 2: Deploy with Terraform
if [ "$SKIP_TERRAFORM" = false ]; then
    log_step "Step 2/2: Deploying infrastructure with Terraform..."

    # Check if terraform.tfvars has been customized
    if grep -q "YOUR_GEMINI_API_KEY_HERE" terraform.tfvars; then
        log_error "Please update terraform.tfvars with your actual values"
        log_error "Required: gemini_api_key, opensearch_endpoint, bucket names"
        exit 1
    fi

    # Initialize Terraform if needed
    if [ ! -d ".terraform" ]; then
        log_info "Initializing Terraform..."
        terraform init
    fi

    # Plan
    log_info "Creating Terraform plan..."
    terraform plan -out=tfplan

    # Apply
    log_info "Applying Terraform changes..."
    terraform apply tfplan

    # Clean up plan file
    rm -f tfplan

    log_info "✓ Terraform deployment complete"
    echo ""
else
    log_step "Step 2/2: Skipping Terraform deployment"
    echo ""
fi

# Summary
log_info "=========================================="
log_info "Deployment Complete!"
log_info "=========================================="

if [ "$SKIP_TERRAFORM" = false ]; then
    log_info ""
    log_info "Resource Summary:"
    terraform output -json | jq -r 'to_entries[] | "\(.key): \(.value.value)"' 2>/dev/null || terraform output

    log_info ""
    log_info "Next Steps:"
    log_info "1. Test Lambda functions:"
    log_info "   aws lambda invoke --function-name simpla-scraper response.json"
    log_info ""
    log_info "2. Monitor CloudWatch Logs:"
    log_info "   aws logs tail /aws/lambda/simpla-processor --follow"
    log_info ""
    log_info "3. Check SQS queues:"
    log_info "   aws sqs list-queues --region $AWS_REGION"
    log_info ""
fi

log_info "=========================================="
