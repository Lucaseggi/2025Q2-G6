#!/bin/bash

echo "Initializing SQS queues..."

# Create the queues with correct names matching the docker-compose environment
awslocal sqs create-queue --queue-name processing-queue
awslocal sqs create-queue --queue-name embedding-queue  
awslocal sqs create-queue --queue-name inserting-queue

echo "SQS queues created successfully!"

# List queues to verify
awslocal sqs list-queues