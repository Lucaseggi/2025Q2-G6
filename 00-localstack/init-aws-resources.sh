#!/bin/bash

echo "Initializing LocalStack resources (SQS queues + S3 buckets)..."

# Wait for LocalStack to be ready
until awslocal sqs list-queues > /dev/null 2>&1; do
    echo "Waiting for LocalStack to be ready..."
    sleep 2
done

echo "LocalStack is ready! Creating resources..."

# Create SQS queues
echo "Creating SQS queues..."
awslocal sqs create-queue --queue-name purifying
awslocal sqs create-queue --queue-name processing
awslocal sqs create-queue --queue-name embedding
awslocal sqs create-queue --queue-name inserting
echo "✓ SQS queues created"

# Create S3 buckets for caching
echo "Creating S3 buckets..."
awslocal s3 mb s3://simpla-scraper-storage
awslocal s3 mb s3://simpla-purifier-storage
awslocal s3 mb s3://simpla-processor-storage
echo "✓ S3 buckets created"

# List resources to verify
echo ""
echo "=== Available SQS Queues ==="
awslocal sqs list-queues

echo ""
echo "=== Available S3 Buckets ==="
awslocal s3 ls

# Create marker file to signal initialization is complete
echo "done" > /tmp/localstack-initialized.txt
echo ""
echo "✓ LocalStack initialization complete!"
