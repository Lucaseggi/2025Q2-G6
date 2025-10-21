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
  -w, --workspace WORKSPACE  Terraform workspace (default: default)
  --skip-lambdas            Skip Lambda JAR builds
  --skip-ecr                Skip ECR deployment
  --skip-terraform          Skip Terraform apply
  --skip-post-deploy        Skip post-deployment EC2 setup
  -h, --help                Show this help message

EXAMPLES:
  # Full deployment (Lambda JARs + ECR + Terraform + EC2 setup)
  ./deploy.sh -a 123456789012

  # Deploy to specific workspace (e.g., cloud-ws for account 965505236489)
  ./deploy.sh -a 965505236489 -w cloud-ws

  # Skip Lambda builds (JARs already built)
  ./deploy.sh -a 123456789012 --skip-lambdas

  # Skip EC2 post-deployment (only infrastructure, no EC2 configuration)
  ./deploy.sh -a 123456789012 --skip-post-deploy

  # Only deploy to ECR
  ./deploy.sh -a 123456789012 --skip-lambdas --skip-terraform --skip-post-deploy

  # Only run Terraform (assumes JARs and images ready)
  ./deploy.sh -a 123456789012 --skip-lambdas --skip-ecr --skip-post-deploy

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
TF_WORKSPACE="default"
SKIP_LAMBDAS=false
SKIP_ECR=false
SKIP_TERRAFORM=false
SKIP_POST_DEPLOY=false
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
        -w|--workspace)
            TF_WORKSPACE="$2"
            shift 2
            ;;
        --skip-lambdas)
            SKIP_LAMBDAS=true
            shift
            ;;
        --skip-ecr)
            SKIP_ECR=true
            shift
            ;;
        --skip-terraform)
            SKIP_TERRAFORM=true
            shift
            ;;
        --skip-post-deploy)
            SKIP_POST_DEPLOY=true
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
log_info "AWS Account:    $AWS_ACCOUNT_ID"
log_info "AWS Region:     $AWS_REGION"
log_info "Image Tag:      $IMAGE_TAG"
log_info "TF Workspace:   $TF_WORKSPACE"
log_info "Skip Lambdas:   $SKIP_LAMBDAS"
log_info "Skip ECR:       $SKIP_ECR"
log_info "Skip TF:        $SKIP_TERRAFORM"
log_info "Skip Post-Deploy: $SKIP_POST_DEPLOY"
log_info "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "terraform.tfvars" ]; then
    log_error "terraform.tfvars not found. Are you in the terraform-lambda directory?"
    exit 1
fi

# Step 0: Update terraform.tfvars with correct account ID
log_step "Step 0: Updating terraform.tfvars with account ID..."
sed -i "s/[0-9]\{12\}\.dkr\.ecr\.${AWS_REGION}\.amazonaws\.com/${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/g" terraform.tfvars
sed -i "s/simpla-\(scraper\|purifier\|processor\)-storage-[0-9]\{12\}/simpla-\1-storage-${AWS_ACCOUNT_ID}/g" terraform.tfvars
log_info "✓ terraform.tfvars updated"
echo ""

# Step 0.5: Build guard JARs
if [ "$SKIP_LAMBDAS" = false ]; then
    log_step "Step 0.5: Building guard JARs..."

    # Create lambda-artifacts directory if it doesn't exist
    mkdir -p lambda-artifacts

    # Detect OS and run appropriate build script
    # Note: build-lambdas.sh should work on most systems including Git Bash on Windows
    if [ -f "./build-lambdas.sh" ]; then
        log_info "Running build-lambdas.sh..."
        ./build-lambdas.sh
    elif [ -f "./build-lambdas.bat" ]; then
        log_info "Running build-lambdas.bat..."
        cmd //c build-lambdas.bat
    else
        log_error "No build script found (build-lambdas.sh or build-lambdas.bat)"
        exit 1
    fi

    log_info "✓ Lambda JARs built"
    echo ""
else
    log_step "Step 0.5: Skipping Lambda JAR builds"

    # Verify JARs exist if skipping
    if [ ! -f "lambda-artifacts/relational-guard-1.0.0.jar" ] || [ ! -f "lambda-artifacts/vectorial-guard-1.0.0.jar" ]; then
        log_warn "Lambda JARs not found in lambda-artifacts/ directory"
        log_warn "Terraform deployment may fail if JARs are required"
    fi
    echo ""
fi

# Step 1: Deploy to ECR
if [ "$SKIP_ECR" = false ]; then
    log_step "Step 1/3: Deploying Docker images to ECR..."

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
    log_step "Step 1/3: Skipping ECR deployment"
    echo ""
fi

# Step 2: Deploy with Terraform
if [ "$SKIP_TERRAFORM" = false ]; then
    log_step "Step 2/3: Deploying infrastructure with Terraform..."

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

    # Select workspace
    log_info "Selecting Terraform workspace: $TF_WORKSPACE"
    terraform workspace select "$TF_WORKSPACE" 2>/dev/null || terraform workspace new "$TF_WORKSPACE"

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
    log_step "Step 2/3: Skipping Terraform deployment"
    echo ""
fi

# Step 3: Post-deployment EC2 setup
if [ "$SKIP_POST_DEPLOY" = false ]; then
    log_step "Step 3/3: Setting up EC2 instances..."

    # Check if post-terraform-deploy.sh exists
    if [ ! -f "ec2-scripts/post-terraform-deploy.sh" ]; then
        log_warn "ec2-scripts/post-terraform-deploy.sh not found, skipping EC2 setup"
    else
        # Check if there's a terraform state (i.e., terraform was run)
        if [ ! -f "terraform.tfstate" ] || [ ! -s "terraform.tfstate" ]; then
            log_warn "No Terraform state found, skipping EC2 setup"
        else
            ./ec2-scripts/post-terraform-deploy.sh
        fi
    fi

    log_info "✓ EC2 setup complete"
    echo ""
else
    log_step "Step 3/3: Skipping post-deployment EC2 setup"
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
