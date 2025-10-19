#!/bin/bash

echo "Initializing LocalStack resources (SQS + S3 + Secrets Manager)..."

# Wait for LocalStack to be ready
until awslocal sqs list-queues > /dev/null 2>&1; do
    echo "Waiting for LocalStack to be ready..."
    sleep 2
done

echo "LocalStack is ready! Creating resources..."

# Load environment variables from dev.env
if [ -f /etc/localstack/init/ready.d/dev.env ]; then
    echo "Loading configuration from dev.env..."
    set -a
    source /etc/localstack/init/ready.d/dev.env
    set +a
else
    echo "Warning: dev.env not found, using defaults"
fi

# Create SQS queues
echo "Creating SQS queues..."
awslocal sqs create-queue --queue-name ${PURIFYING_QUEUE_NAME:-purifying}
awslocal sqs create-queue --queue-name ${PROCESSING_QUEUE_NAME:-processing}
awslocal sqs create-queue --queue-name ${EMBEDDING_QUEUE_NAME:-embedding}
awslocal sqs create-queue --queue-name ${INSERTING_QUEUE_NAME:-inserting}
echo "✓ SQS queues created"

# Create S3 buckets for caching
echo "Creating S3 buckets..."
awslocal s3 mb s3://${SCRAPER_BUCKET:-simpla-scraper-storage}
awslocal s3 mb s3://${PURIFIER_BUCKET:-simpla-purifier-storage}
awslocal s3 mb s3://${PROCESSOR_BUCKET:-simpla-processor-storage}
echo "✓ S3 buckets created"

# Create Secrets Manager secrets
echo "Creating Secrets Manager secrets..."

# 1. simpla/shared/aws-config
awslocal secretsmanager create-secret \
    --name "simpla/shared/aws-config" \
    --secret-string "{
        \"aws_region\": \"${AWS_DEFAULT_REGION:-us-east-1}\",
        \"sqs_endpoint\": \"${SQS_ENDPOINT:-http://localstack:4566}\",
        \"s3_endpoint\": \"${S3_ENDPOINT:-http://localstack:4566}\",
        \"aws_access_key_id\": \"${AWS_ACCESS_KEY_ID:-test}\",
        \"aws_secret_access_key\": \"${AWS_SECRET_ACCESS_KEY:-test}\"
    }" 2>&1 | grep -v "ResourceExistsException" || echo "  → aws-config exists, skipping"

# 2. simpla/shared/queue-names
awslocal secretsmanager create-secret \
    --name "simpla/shared/queue-names" \
    --secret-string "{
        \"purifying\": \"${PURIFYING_QUEUE_NAME:-purifying}\",
        \"processing\": \"${PROCESSING_QUEUE_NAME:-processing}\",
        \"embedding\": \"${EMBEDDING_QUEUE_NAME:-embedding}\",
        \"inserting\": \"${INSERTING_QUEUE_NAME:-inserting}\"
    }" 2>&1 | grep -v "ResourceExistsException" || echo "  → queue-names exists, skipping"

# 3. simpla/shared/s3-buckets
awslocal secretsmanager create-secret \
    --name "simpla/shared/s3-buckets" \
    --secret-string "{
        \"scraper_bucket\": \"${SCRAPER_BUCKET:-simpla-scraper-storage}\",
        \"purifier_bucket\": \"${PURIFIER_BUCKET:-simpla-purifier-storage}\",
        \"processor_bucket\": \"${PROCESSOR_BUCKET:-simpla-processor-storage}\"
    }" 2>&1 | grep -v "ResourceExistsException" || echo "  → s3-buckets exists, skipping"

# 4. simpla/api-keys/gemini
awslocal secretsmanager create-secret \
    --name "simpla/api-keys/gemini" \
    --secret-string "{
        \"api_key\": \"${GEMINI_API_KEY:-}\"
    }" 2>&1 | grep -v "ResourceExistsException" || echo "  → gemini api key exists, skipping"

# 5. simpla/services/config
awslocal secretsmanager create-secret \
    --name "simpla/services/config" \
    --secret-string "{
        \"opensearch_endpoint\": \"${OPENSEARCH_ENDPOINT:-http://opensearch:9200}\",
        \"scraper_port\": ${SCRAPER_PORT:-8003},
        \"purifier_port\": ${PURIFIER_PORT:-8004},
        \"processor_port\": ${PROCESSOR_PORT:-8005},
        \"embedder_port\": ${EMBEDDER_PORT:-8001},
        \"inserter_storage_client_type\": \"${STORAGE_CLIENT_TYPE:-rest}\"
    }" 2>&1 | grep -v "ResourceExistsException" || echo "  → services config exists, skipping"

echo "✓ Secrets Manager secrets created"

# List resources to verify
echo ""
echo "=== Available SQS Queues ==="
awslocal sqs list-queues

echo ""
echo "=== Available S3 Buckets ==="
awslocal s3 ls

echo ""
echo "=== Available Secrets ==="
awslocal secretsmanager list-secrets --query 'SecretList[].Name' --output table

# Create marker file to signal initialization is complete
echo "done" > /tmp/localstack-initialized.txt
echo ""
echo "✓ LocalStack initialization complete!"
