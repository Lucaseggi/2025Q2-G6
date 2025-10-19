# SQS Queues for Simpla Pipeline
# Creates queues for each stage: purifying -> processing -> embedding -> inserting

# Purifying Queue (receives messages from scraper)
resource "aws_sqs_queue" "purifying" {
  name                       = var.purifying_queue_name
  visibility_timeout_seconds = 900  # 15 minutes (matches Lambda timeout)
  message_retention_seconds  = 1209600  # 14 days
  receive_wait_time_seconds  = 20  # Long polling

  # Dead letter queue configuration
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.purifying_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name        = "simpla-purifying-queue"
    Environment = var.environment
    Service     = "purifier"
  }
}

# Purifying Dead Letter Queue
resource "aws_sqs_queue" "purifying_dlq" {
  name                      = "${var.purifying_queue_name}-dlq"
  message_retention_seconds = 1209600  # 14 days

  tags = {
    Name        = "simpla-purifying-dlq"
    Environment = var.environment
    Service     = "purifier"
  }
}

# Processing Queue (receives messages from purifier)
resource "aws_sqs_queue" "processing" {
  name                       = var.processing_queue_name
  visibility_timeout_seconds = 900  # 15 minutes for LLM processing
  message_retention_seconds  = 1209600
  receive_wait_time_seconds  = 20

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.processing_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name        = "simpla-processing-queue"
    Environment = var.environment
    Service     = "processor"
  }
}

# Processing Dead Letter Queue
resource "aws_sqs_queue" "processing_dlq" {
  name                      = "${var.processing_queue_name}-dlq"
  message_retention_seconds = 1209600

  tags = {
    Name        = "simpla-processing-dlq"
    Environment = var.environment
    Service     = "processor"
  }
}

# Embedding Queue (receives messages from processor)
resource "aws_sqs_queue" "embedding" {
  name                       = var.embedding_queue_name
  visibility_timeout_seconds = 600  # 10 minutes
  message_retention_seconds  = 1209600
  receive_wait_time_seconds  = 20

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.embedding_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name        = "simpla-embedding-queue"
    Environment = var.environment
    Service     = "embedder"
  }
}

# Embedding Dead Letter Queue
resource "aws_sqs_queue" "embedding_dlq" {
  name                      = "${var.embedding_queue_name}-dlq"
  message_retention_seconds = 1209600

  tags = {
    Name        = "simpla-embedding-dlq"
    Environment = var.environment
    Service     = "embedder"
  }
}

# Inserting Queue (receives messages from embedder)
resource "aws_sqs_queue" "inserting" {
  name                       = var.inserting_queue_name
  visibility_timeout_seconds = 600  # 10 minutes
  message_retention_seconds  = 1209600
  receive_wait_time_seconds  = 20

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.inserting_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name        = "simpla-inserting-queue"
    Environment = var.environment
    Service     = "inserter"
  }
}

# Inserting Dead Letter Queue
resource "aws_sqs_queue" "inserting_dlq" {
  name                      = "${var.inserting_queue_name}-dlq"
  message_retention_seconds = 1209600

  tags = {
    Name        = "simpla-inserting-dlq"
    Environment = var.environment
    Service     = "inserter"
  }
}
