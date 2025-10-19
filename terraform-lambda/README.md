# Simpla Lambda Deployment - Terraform Configuration

This directory contains Terraform configuration to deploy the Simpla data extraction pipeline to AWS Lambda.

## Architecture Overview

The deployment creates a serverless data processing pipeline with the following components:

```
Scraper → [purifying queue] → Purifier → [processing queue] → Processor → [embedding queue] → Embedder → [inserting queue] → Inserter
```

### AWS Resources Created

#### 1. SQS Queues (Foundation)
- `purifying` - Messages from scraper to purifier
- `processing` - Messages from purifier to processor
- `embedding` - Messages from processor to embedder
- `inserting` - Messages from embedder to inserter
- Dead letter queues for each (automatic retry handling)

#### 2. S3 Buckets (Foundation)
- `simpla-scraper-storage` - Cache for scraped HTML
- `simpla-purifier-storage` - Cache for cleaned text
- `simpla-processor-storage` - Cache for structured data
- All with versioning, encryption, and lifecycle policies

#### 3. Secrets Manager (Uses outputs from #1 and #2)
- `simpla/shared/aws-config` - AWS configuration
- `simpla/shared/queue-names` - SQS queue names
- `simpla/shared/s3-buckets` - S3 bucket names
- `simpla/api-keys/gemini` - Gemini API key (sensitive)
- `simpla/services/config` - Service endpoints and configuration

#### 4. Lambda Functions (Uses outputs from #3)
- `simpla-scraper` - Web scraping service
- `simpla-purifier` - Text cleaning service (SQS + API triggers)
- `simpla-processor` - LLM-based document structuring (SQS + API triggers)
- `simpla-embedder` - Text embedding generation (SQS + API triggers)
- `simpla-inserter` - Database insertion service (SQS trigger)

#### 5. Event Source Mappings
- Automatic SQS → Lambda triggers
- Batch processing configuration
- Error handling and retry logic

## Prerequisites

1. **AWS CLI configured** with appropriate credentials
   ```bash
   aws configure
   ```

2. **Docker images pushed to ECR** (run `deploy-to-ecr.sh` first)
   ```bash
   # Example: Deploy all services
   ./deploy-to-ecr.sh -a YOUR_AWS_ACCOUNT_ID all

   # Or deploy individually
   ./deploy-to-ecr.sh -a YOUR_AWS_ACCOUNT_ID processor
   ```

3. **Terraform installed** (version >= 1.0)
   ```bash
   terraform --version
   ```

4. **OpenSearch domain** (AWS OpenSearch Service or self-hosted)
   - Required for embedder and inserter services
   - Update `opensearch_endpoint` in `terraform.tfvars`

5. **Gemini API key** for LLM services
   - Get from: https://makersuite.google.com/app/apikey
   - Update `gemini_api_key` in `terraform.tfvars`

## Deployment Order

Terraform automatically handles the dependency chain:

```
Step 1: SQS Queues + S3 Buckets (parallel creation)
   ↓
Step 2: Secrets Manager (references queue/bucket names)
   ↓
Step 3: Lambda Functions (read from Secrets Manager)
   ↓
Step 4: SQS Event Source Mappings
```

## Deployment Steps

### 1. Configure Variables

Edit `terraform.tfvars` with your values:

```hcl
# Required changes:
aws_region = "us-east-1"

# Update bucket names (must be globally unique)
scraper_bucket_name   = "simpla-scraper-storage-YOUR-ACCOUNT-ID"
purifier_bucket_name  = "simpla-purifier-storage-YOUR-ACCOUNT-ID"
processor_bucket_name = "simpla-processor-storage-YOUR-ACCOUNT-ID"

# Add your API key
gemini_api_key = "YOUR_GEMINI_API_KEY"

# Add your OpenSearch endpoint
opensearch_endpoint = "https://your-domain.us-east-1.es.amazonaws.com"
```

### 2. Initialize Terraform

```bash
cd terraform-lambda
terraform init
```

### 3. Review Deployment Plan

```bash
terraform plan
```

This shows all resources that will be created.

### 4. Deploy Infrastructure

```bash
terraform apply
```

Type `yes` when prompted.

### 5. Verify Deployment

Check outputs:
```bash
terraform output
```

Test Lambda functions:
```bash
# Test scraper
aws lambda invoke --function-name simpla-scraper response.json

# Check queue status
aws sqs get-queue-attributes \
  --queue-url $(terraform output -raw purifying_queue_url) \
  --attribute-names All
```

## File Structure

```
terraform-lambda/
├── main.tf              # Provider, IAM roles, Lambda functions
├── sqs.tf               # SQS queue definitions
├── s3.tf                # S3 bucket configurations
├── secrets.tf           # Secrets Manager resources
├── event_sources.tf     # SQS → Lambda event mappings
├── variables.tf         # Variable definitions
├── outputs.tf           # Output values
├── terraform.tfvars     # Variable values (customize this)
└── README.md           # This file
```

## Configuration Details

### Lambda Resource Allocation

| Service   | Memory | Timeout | Concurrency | Batch Size |
|-----------|--------|---------|-------------|------------|
| Scraper   | 512 MB | 5 min   | N/A         | N/A        |
| Purifier  | 1 GB   | 5 min   | 10          | 1          |
| Processor | 2 GB   | 15 min  | 5           | 1          |
| Embedder  | 1 GB   | 5 min   | 20          | 5          |
| Inserter  | 512 MB | 5 min   | 15          | 10         |

### SQS Configuration

- **Visibility Timeout**: Matches Lambda timeout
- **Message Retention**: 14 days
- **Long Polling**: Enabled (20 seconds)
- **Dead Letter Queue**: Enabled (3 retries)

### S3 Lifecycle Policies

- **Expiration**: 90 days
- **Versioning**: Enabled
- **Encryption**: AES256
- **Public Access**: Blocked

## Cost Estimation

Monthly costs (approximate, us-east-1):

- **Lambda**: ~$50-200 (depends on usage)
- **SQS**: ~$1-5 (first 1M requests free)
- **S3**: ~$5-20 (depends on data volume)
- **Secrets Manager**: ~$2 (5 secrets)
- **Data Transfer**: Variable

**Estimated Total**: $60-230/month for moderate usage

## Updating Lambda Functions

After building new images:

```bash
# 1. Push new images to ECR
./deploy-to-ecr.sh -a YOUR_AWS_ACCOUNT_ID -u processor

# 2. Update Lambda to use new image
terraform apply
```

Or update Lambda directly:
```bash
aws lambda update-function-code \
  --function-name simpla-processor \
  --image-uri YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/simpla-processor:latest
```

## Monitoring

### CloudWatch Logs

Logs are automatically created for each Lambda:
```bash
# View processor logs
aws logs tail /aws/lambda/simpla-processor --follow

# View purifier logs
aws logs tail /aws/lambda/simpla-purifier --follow
```

### SQS Metrics

Monitor queue depth:
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS \
  --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=processing \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Average
```

## Troubleshooting

### Lambda Functions Not Triggering

1. Check SQS event source mapping:
   ```bash
   aws lambda list-event-source-mappings \
     --function-name simpla-purifier
   ```

2. Verify IAM permissions:
   ```bash
   aws iam get-role-policy \
     --role-name simpla-lambda-execution-role \
     --policy-name simpla-lambda-permissions
   ```

### Secrets Not Found

Check if secrets exist:
```bash
aws secretsmanager list-secrets | grep simpla
```

Get secret value:
```bash
aws secretsmanager get-secret-value \
  --secret-id simpla/shared/queue-names
```

### High Lambda Costs

- Review CloudWatch logs for errors causing retries
- Check dead letter queues for failed messages
- Adjust concurrency limits in `event_sources.tf`

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning**: This will delete all queues, buckets, and Lambda functions!

## Security Best Practices

1. **API Keys**: Store in AWS Secrets Manager (not in terraform.tfvars)
   ```bash
   aws secretsmanager put-secret-value \
     --secret-id simpla/api-keys/gemini \
     --secret-string '{"api_key":"YOUR_KEY"}'
   ```

2. **S3 Buckets**: Public access is blocked by default

3. **IAM Roles**: Follow least privilege principle

4. **VPC**: Consider deploying Lambdas in VPC for additional security

5. **Encryption**: All data encrypted at rest (S3, Secrets Manager)

## Next Steps

1. Set up CloudWatch alarms for queue depth
2. Configure Lambda reserved concurrency
3. Set up API Gateway for HTTP endpoints (optional)
4. Deploy OpenSearch domain via Terraform
5. Add monitoring dashboard

## Support

For issues or questions:
- Check CloudWatch Logs
- Review Terraform plan output
- Verify AWS resource limits
- Check service quotas in AWS Console
