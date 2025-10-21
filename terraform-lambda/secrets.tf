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
    opensearch_endpoint          = "${aws_instance.vector_db.private_ip}:9200"
    inserter_storage_client_type = var.storage_client_type
    # Lambda port placeholders (not used but required by config validation)
    scraper_port   = 8001
    purifier_port  = 8002
    processor_port = 8003
    embedder_port  = 8004
    inserter_port  = 8005
  })
}

# 6. Embedder API Endpoints Secret
# This secret stores the API Gateway URLs for the embedder service
# Other services can read these URLs to connect to the embedder
resource "aws_secretsmanager_secret" "embedder_endpoints" {
  name        = "simpla/services/embedder-endpoints"
  description = "API Gateway endpoints for embedder service"

  tags = {
    Name        = "simpla-embedder-endpoints"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "embedder_endpoints" {
  secret_id = aws_secretsmanager_secret.embedder_endpoints.id

  secret_string = jsonencode({
    # Full API URLs including endpoints
    embedder_api_url = module.embedder_api.api_endpoint
    health_endpoint  = "${module.embedder_api.api_endpoint}/health"
    embed_endpoint   = "${module.embedder_api.api_endpoint}/embed"
  })

  # Ensure embedder is deployed before creating the secret
  depends_on = [
    module.embedder_api
  ]
}

# 7. Guard API Endpoints Secret
# This secret stores the API Gateway URLs for relational and vectorial guards
# These are automatically populated from the guard Lambda deployments
# The inserter service reads these URLs to connect to the guards
resource "aws_secretsmanager_secret" "guard_endpoints" {
  name        = "simpla/services/guard-endpoints"
  description = "API Gateway endpoints for relational and vectorial guards"

  tags = {
    Name        = "simpla-guard-endpoints"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "guard_endpoints" {
  secret_id = aws_secretsmanager_secret.guard_endpoints.id

  secret_string = jsonencode({
    # Full API URLs including the base path (e.g., https://xxx.execute-api.us-east-1.amazonaws.com/prod/api/v1/relational)
    relational_api_url = "${module.relational_guard.api_endpoint}/api/v1/relational"
    vectorial_api_url  = "${module.vectorial_guard.api_endpoint}/api/v1/vectorial"
  })

  # Ensure guards are deployed before creating the secret
  depends_on = [
    module.relational_guard,
    module.vectorial_guard
  ]
}

# 8. Answer Generator Endpoints Secret
# This secret stores the API Gateway URLs for answer generator service
# Other services can read these URLs to connect to the answer generator
resource "aws_secretsmanager_secret" "answer_generator_endpoints" {
  name        = "simpla/services/answer-generator-endpoints"
  description = "API Gateway endpoints for answer generator service"

  tags = {
    Name        = "simpla-answer-generator-endpoints"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "answer_generator_endpoints" {
  secret_id = aws_secretsmanager_secret.answer_generator_endpoints.id

  secret_string = jsonencode({
    # Full API URLs including endpoints
    answer_generator_api_url = module.answer_generator_api.api_endpoint
    health_endpoint          = "${module.answer_generator_api.api_endpoint}/health"
    question_endpoint        = "${module.answer_generator_api.api_endpoint}/question"
  })

  # Ensure answer generator is deployed before creating the secret
  depends_on = [
    module.answer_generator_api
  ]
}
