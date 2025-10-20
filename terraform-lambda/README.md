# Simpla Lambda Deployment

## Quick Start

```bash
./deploy.sh -a <AWS_ACCOUNT_ID>
```

This single command will:
1. Update terraform.tfvars with your AWS account ID
2. Build guard JARs (relational-guard, vectorial-guard)
3. Deploy all Docker images to ECR (scraper, purifier, processor, embedder, inserter)
4. Apply Terraform to create all AWS infrastructure

## Prerequisites

- AWS CLI configured with credentials
- Docker installed and running
- Terraform installed
- Maven installed (for guard JARs)

## What Gets Deployed

- **Lambdas**: scraper, purifier, processor, embedder, inserter, relational-guard, vectorial-guard
- **SQS Queues**: purifying, processing, embedding, inserting (with DLQs)
- **S3 Buckets**: scraper-storage, purifier-storage, processor-storage, lambda-artifacts
- **API Gateway**: REST endpoints for both guards
- **Secrets Manager**: Guard API URLs, queue names, S3 buckets, Gemini API key

## Testing

Create a test payload file:
```bash
cat > /tmp/test-scrape.json << 'EOF'
{
  "httpMethod": "POST",
  "path": "/scrape",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": "{\"infoleg_id\": 183532, \"force\": false}"
}
EOF
```

Invoke the scraper:
```bash
aws lambda invoke \
  --function-name simpla-scraper \
  --payload fileb:///tmp/test-scrape.json \
  --region us-east-1 \
  response.json
```

Monitor queues:
```bash
aws logs tail /aws/lambda/simpla-scraper --since 5m --format short --region us-east-1 | tail -30
aws logs tail /aws/lambda/simpla-purifier --since 5m --format short --region us-east-1 | tail -30
aws logs tail /aws/lambda/simpla-processor --since 5m --format short --region us-east-1 | tail -30
aws logs tail /aws/lambda/simpla-embedder --since 5m --format short --region us-east-1 | tail -30
aws logs tail /aws/lambda/simpla-inserter --since 5m --format short --region us-east-1 | tail -30
```

## Configuration

Edit `terraform.tfvars` to customize:
- Gemini API key (required)
- Database hosts (placeholder until RDS/OpenSearch created)

**Note:** ECR image URIs and S3 bucket names are automatically updated by deploy.sh

## Important Notes

- Guards will fail until RDS (PostgreSQL) and OpenSearch are deployed by your team
- The inserter will successfully connect to guards but they will return errors due to missing databases
- This is expected behavior - guards are deployed and reachable via REST APIs
- All infrastructure is deployed to us-east-1 by default

## Cleanup

```bash
terraform destroy
```
