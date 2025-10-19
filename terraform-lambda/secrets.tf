# AWS Secrets Manager Configuration
# Creates secrets that reference SQS queues and S3 buckets created above
# This matches the LocalStack init-aws-resources.sh structure

# 1. AWS Configuration Secret
resource "aws_secretsmanager_secret" "aws_config" {
  name        = "simpla/shared/aws-config"
  description = "AWS configuration for Simpla services"

  tags = {
    Name        = "simpla-aws-config"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "aws_config" {
  secret_id = aws_secretsmanager_secret.aws_config.id

  secret_string = jsonencode({
    aws_region             = var.aws_region
    aws_access_key_id      = ""  # Not needed for Lambda execution
    aws_secret_access_key  = ""  # Not needed for Lambda execution
    sqs_endpoint           = "https://sqs.${var.aws_region}.amazonaws.com"
    s3_endpoint            = "https://s3.${var.aws_region}.amazonaws.com"
  })
}

# 2. Queue Names Secret (references SQS queue names)
resource "aws_secretsmanager_secret" "queue_names" {
  name        = "simpla/shared/queue-names"
  description = "SQS queue names for Simpla pipeline"

  tags = {
    Name        = "simpla-queue-names"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "queue_names" {
  secret_id = aws_secretsmanager_secret.queue_names.id

  secret_string = jsonencode({
    purifying = aws_sqs_queue.purifying.name
    processing = aws_sqs_queue.processing.name
    embedding  = aws_sqs_queue.embedding.name
    inserting  = aws_sqs_queue.inserting.name
  })

  # Ensure queues are created before this secret
  depends_on = [
    aws_sqs_queue.purifying,
    aws_sqs_queue.processing,
    aws_sqs_queue.embedding,
    aws_sqs_queue.inserting
  ]
}

# 3. S3 Buckets Secret (references S3 bucket names)
resource "aws_secretsmanager_secret" "s3_buckets" {
  name        = "simpla/shared/s3-buckets"
  description = "S3 bucket names for Simpla caching"

  tags = {
    Name        = "simpla-s3-buckets"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "s3_buckets" {
  secret_id = aws_secretsmanager_secret.s3_buckets.id

  secret_string = jsonencode({
    scraper_bucket   = aws_s3_bucket.scraper_storage.id
    purifier_bucket  = aws_s3_bucket.purifier_storage.id
    processor_bucket = aws_s3_bucket.processor_storage.id
  })

  # Ensure buckets are created before this secret
  depends_on = [
    aws_s3_bucket.scraper_storage,
    aws_s3_bucket.purifier_storage,
    aws_s3_bucket.processor_storage
  ]
}

# 4. Gemini API Key Secret
resource "aws_secretsmanager_secret" "gemini_api_key" {
  name        = "simpla/api-keys/gemini"
  description = "Gemini API key for LLM and embedding services"

  tags = {
    Name        = "simpla-gemini-api-key"
    Environment = var.environment
    Sensitive   = "true"
  }
}

resource "aws_secretsmanager_secret_version" "gemini_api_key" {
  secret_id = aws_secretsmanager_secret.gemini_api_key.id

  secret_string = jsonencode({
    api_key = var.gemini_api_key
  })
}

# 5. Services Configuration Secret
resource "aws_secretsmanager_secret" "services_config" {
  name        = "simpla/services/config"
  description = "Service configuration for Simpla pipeline"

  tags = {
    Name        = "simpla-services-config"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "services_config" {
  secret_id = aws_secretsmanager_secret.services_config.id

  secret_string = jsonencode({
    opensearch_endpoint          = var.opensearch_endpoint
    inserter_storage_client_type = var.storage_client_type
    # Lambda port placeholders (not used but required by config validation)
    scraper_port   = 8001
    purifier_port  = 8002
    processor_port = 8003
    embedder_port  = 8004
    inserter_port  = 8005
  })
}
