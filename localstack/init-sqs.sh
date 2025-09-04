#!/bin/bash

echo "Creating SQS queues..."

# Create the three queues needed for the pipeline
awslocal sqs create-queue --queue-name processing-queue
awslocal sqs create-queue --queue-name embedding-queue  
awslocal sqs create-queue --queue-name inserting-queue

echo "SQS queues created successfully!"

# List all queues to verify
echo "Available queues:"
awslocal sqs list-queues