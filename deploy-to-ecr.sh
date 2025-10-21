#!/bin/bash
set -e

# Global deployment script for deploying microservices to ECR for Lambda
# Supports: scraper, purifier, processor, embedder

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
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
Usage: ./deploy-to-ecr.sh [OPTIONS] SERVICE

Deploy microservices to ECR for AWS Lambda deployment.

SERVICES:
  processor         - 03-processor (LLM-based document structuring)
  purifier          - 02-purifier (Text cleaning and purification)
  scraper           - 01-scraper (Web scraping service)
  embedder          - 04-embedder (Text embedding service)
  answer-generator  - answer-generator (RAG-based question answering)
  all               - Deploy all services

OPTIONS:
  -r, --region REGION        AWS region (default: us-east-1)
  -a, --account ACCOUNT_ID   AWS account ID (required)
  -t, --tag TAG             Image tag (default: latest)
  -s, --skip-test           Skip local testing
  -u, --update-lambda       Update Lambda function after push
  -h, --help                Show this help message

EXAMPLES:
  # Deploy processor to ECR
  ./deploy-to-ecr.sh -a 123456789012 processor

  # Deploy all services with custom tag
  ./deploy-to-ecr.sh -a 123456789012 -t v1.2.3 all

  # Deploy and update Lambda function
  ./deploy-to-ecr.sh -a 123456789012 -u processor

ENVIRONMENT VARIABLES:
  AWS_ACCOUNT_ID    - AWS account ID (alternative to -a flag)
  AWS_REGION        - AWS region (alternative to -r flag)
  IMAGE_TAG         - Image tag (alternative to -t flag)

EOF
}

# Service configuration
declare -A SERVICE_DIRS=(
    ["processor"]="03-processor"
    ["purifier"]="02-purifier"
    ["scraper"]="01-scraper"
    ["embedder"]="04-embedder"
    ["inserter"]="05-inserter"
    ["answer-generator"]="answer-generator"
    ["db-seeder"]="relational-db-seeder"
)

declare -A SERVICE_REPOS=(
    ["processor"]="simpla-processor"
    ["purifier"]="simpla-purifier"
    ["scraper"]="simpla-scraper"
    ["embedder"]="simpla-embedder"
    ["inserter"]="simpla-inserter"
    ["answer-generator"]="simpla-answer-generator"
    ["db-seeder"]="simpla-relational-db-seeder"
)

declare -A SERVICE_LAMBDA_NAMES=(
    ["processor"]="simpla-processor"
    ["purifier"]="simpla-purifier"
    ["scraper"]="simpla-scraper"
    ["embedder"]="simpla-embedder"
    ["inserter"]="simpla-inserter"
    ["answer-generator"]="simpla-answer-generator"
    ["db-seeder"]="relational-db-seeder"
)

# Parse command line arguments
SKIP_LOCAL_TEST=false
UPDATE_LAMBDA=false
SERVICE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -a|--account)
            AWS_ACCOUNT_ID="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -s|--skip-test)
            SKIP_LOCAL_TEST=true
            shift
            ;;
        -u|--update-lambda)
            UPDATE_LAMBDA=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            SERVICE="$1"
            shift
            ;;
    esac
done

# Validate required variables
if [ -z "$AWS_ACCOUNT_ID" ]; then
    log_error "AWS_ACCOUNT_ID is required"
    echo ""
    print_usage
    exit 1
fi

if [ -z "$SERVICE" ]; then
    log_error "SERVICE argument is required"
    echo ""
    print_usage
    exit 1
fi

# Validate service
if [ "$SERVICE" != "all" ] && [ -z "${SERVICE_DIRS[$SERVICE]}" ]; then
    log_error "Invalid service: $SERVICE"
    log_info "Valid services: ${!SERVICE_DIRS[@]} all"
    exit 1
fi

# Derived variables
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Function to deploy a single service
deploy_service() {
    local service=$1
    local service_dir="${SERVICE_DIRS[$service]}"
    local ecr_repo="${SERVICE_REPOS[$service]}"
    local lambda_name="${SERVICE_LAMBDA_NAMES[$service]}"
    local full_image_name="${ECR_URI}/${ecr_repo}:${IMAGE_TAG}"

    log_info "=========================================="
    log_info "Deploying: $service"
    log_info "=========================================="
    log_info "Service Directory: $service_dir"
    log_info "ECR Repository:    $ecr_repo"
    log_info "Image Tag:         $IMAGE_TAG"
    log_info "Full Image Name:   $full_image_name"
    log_info "=========================================="

    # Check if service directory exists
    if [ ! -d "$service_dir" ]; then
        log_error "Service directory not found: $service_dir"
        return 1
    fi

    # Check if Dockerfile.lambda exists
    if [ ! -f "$service_dir/Dockerfile.lambda" ]; then
        log_warn "Dockerfile.lambda not found in $service_dir"
        log_warn "Skipping $service (not yet migrated to Lambda)"
        return 0
    fi

    # Step 1: Check/create ECR repository
    log_step "Step 1/6: Checking ECR repository..."
    if aws ecr describe-repositories \
        --repository-names "$ecr_repo" \
        --region "$AWS_REGION" > /dev/null 2>&1; then
        log_info "ECR repository '$ecr_repo' exists"
    else
        log_warn "Creating ECR repository '$ecr_repo'..."
        aws ecr create-repository \
            --repository-name "$ecr_repo" \
            --region "$AWS_REGION" \
            --image-scanning-configuration scanOnPush=true \
            --encryption-configuration encryptionType=AES256 > /dev/null
        log_info "ECR repository created"
    fi

    # Step 2: Authenticate Docker to ECR (only once)
    if [ "$ECR_AUTHENTICATED" != "true" ]; then
        log_step "Step 2/6: Authenticating Docker to ECR..."
        aws ecr get-login-password --region "$AWS_REGION" | \
            docker login --username AWS --password-stdin "$ECR_URI" > /dev/null 2>&1
        log_info "Docker authenticated"
        export ECR_AUTHENTICATED=true
    else
        log_step "Step 2/6: Docker already authenticated (skipped)"
    fi

    # Step 3: Build Docker image
    log_step "Step 3/6: Building Docker image..."
    docker build \
        -f "$service_dir/Dockerfile.lambda" \
        -t "$ecr_repo:$IMAGE_TAG" \
        -t "$full_image_name" \
        "$service_dir" > /dev/null 2>&1
    log_info "Docker image built"

    # Step 4: Test image locally (optional)
    if [ "$SKIP_LOCAL_TEST" = false ]; then
        log_step "Step 4/6: Local testing (skipped)"
        log_info "To test locally: docker run -p 9000:8080 $ecr_repo:$IMAGE_TAG"
    else
        log_step "Step 4/6: Local testing (skipped)"
    fi

    # Step 5: Push to ECR
    log_step "Step 5/6: Pushing image to ECR..."
    docker push "$full_image_name" > /dev/null 2>&1
    log_info "Image pushed to ECR"

    # Get image digest
    local image_digest
    image_digest=$(aws ecr describe-images \
        --repository-name "$ecr_repo" \
        --image-ids imageTag="$IMAGE_TAG" \
        --region "$AWS_REGION" \
        --query 'imageDetails[0].imageDigest' \
        --output text 2>/dev/null || echo "N/A")

    log_info "Image digest: $image_digest"

    # Step 6: Update Lambda function (optional)
    if [ "$UPDATE_LAMBDA" = true ]; then
        log_step "Step 6/6: Updating Lambda function..."

        if aws lambda get-function \
            --function-name "$lambda_name" \
            --region "$AWS_REGION" > /dev/null 2>&1; then

            log_info "Updating Lambda function '$lambda_name'..."
            aws lambda update-function-code \
                --function-name "$lambda_name" \
                --image-uri "$full_image_name" \
                --region "$AWS_REGION" > /dev/null

            log_info "Waiting for update to complete..."
            aws lambda wait function-updated \
                --function-name "$lambda_name" \
                --region "$AWS_REGION"

            log_info "Lambda function updated successfully"
        else
            log_warn "Lambda function '$lambda_name' not found (create with Terraform first)"
        fi
    else
        log_step "Step 6/6: Lambda update (skipped, use -u to enable)"
    fi

    log_info "=========================================="
    log_info "✓ $service deployment complete!"
    log_info "=========================================="
    echo ""
}

# Main execution
log_info "=========================================="
log_info "ECR Deployment Script"
log_info "=========================================="
log_info "AWS Region:     $AWS_REGION"
log_info "AWS Account:    $AWS_ACCOUNT_ID"
log_info "Image Tag:      $IMAGE_TAG"
log_info "Update Lambda:  $UPDATE_LAMBDA"
log_info "=========================================="
echo ""

# Deploy service(s)
if [ "$SERVICE" = "all" ]; then
    log_info "Deploying all services..."
    echo ""

    for svc in "${!SERVICE_DIRS[@]}"; do
        deploy_service "$svc"
    done

    log_info "=========================================="
    log_info "All services deployed successfully!"
    log_info "=========================================="
else
    deploy_service "$SERVICE"
fi

# Summary
echo ""
log_info "Next steps:"
log_info "1. Verify images in ECR: aws ecr list-images --repository-name simpla-processor"
log_info "2. Deploy infrastructure: cd terraform && terraform apply"
log_info "3. Update Lambda: ./deploy-to-ecr.sh -a $AWS_ACCOUNT_ID -u $SERVICE"
log_info ""
