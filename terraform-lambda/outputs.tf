# ============================================================================
# Lambda Function Outputs
# ============================================================================

output "scraper_function_name" {
  description = "Name of the scraper Lambda function"
  value       = aws_lambda_function.scraper.function_name
}

output "purifier_function_name" {
  description = "Name of the purifier Lambda function"
  value       = aws_lambda_function.purifier.function_name
}

output "processor_function_name" {
  description = "Name of the processor Lambda function"
  value       = aws_lambda_function.processor.function_name
}

output "embedder_function_name" {
  description = "Name of the embedder Lambda function"
  value       = module.embedder_api.lambda_function_name
}

output "inserter_function_name" {
  description = "Name of the inserter Lambda function"
  value       = aws_lambda_function.inserter.function_name
}

output "scraper_arn" {
  description = "ARN of the scraper Lambda function"
  value       = aws_lambda_function.scraper.arn
}

output "purifier_arn" {
  description = "ARN of the purifier Lambda function"
  value       = aws_lambda_function.purifier.arn
}

output "processor_arn" {
  description = "ARN of the processor Lambda function"
  value       = aws_lambda_function.processor.arn
}

output "embedder_arn" {
  description = "ARN of the embedder Lambda function"
  value       = module.embedder_api.lambda_function_arn
}

output "inserter_arn" {
  description = "ARN of the inserter Lambda function"
  value       = aws_lambda_function.inserter.arn
}

# ============================================================================
# SQS Queue Outputs
# ============================================================================

output "purifying_queue_url" {
  description = "URL of the purifying SQS queue"
  value       = aws_sqs_queue.purifying.url
}

output "processing_queue_url" {
  description = "URL of the processing SQS queue"
  value       = aws_sqs_queue.processing.url
}

output "embedding_queue_url" {
  description = "URL of the embedding SQS queue"
  value       = aws_sqs_queue.embedding.url
}

output "inserting_queue_url" {
  description = "URL of the inserting SQS queue"
  value       = aws_sqs_queue.inserting.url
}

output "purifying_queue_arn" {
  description = "ARN of the purifying SQS queue"
  value       = aws_sqs_queue.purifying.arn
}

output "processing_queue_arn" {
  description = "ARN of the processing SQS queue"
  value       = aws_sqs_queue.processing.arn
}

output "embedding_queue_arn" {
  description = "ARN of the embedding SQS queue"
  value       = aws_sqs_queue.embedding.arn
}

output "inserting_queue_arn" {
  description = "ARN of the inserting SQS queue"
  value       = aws_sqs_queue.inserting.arn
}

# ============================================================================
# S3 Bucket Outputs
# ============================================================================

output "scraper_bucket_name" {
  description = "Name of the scraper S3 storage bucket"
  value       = aws_s3_bucket.scraper_storage.id
}

output "purifier_bucket_name" {
  description = "Name of the purifier S3 storage bucket"
  value       = aws_s3_bucket.purifier_storage.id
}

output "processor_bucket_name" {
  description = "Name of the processor S3 storage bucket"
  value       = aws_s3_bucket.processor_storage.id
}

output "scraper_bucket_arn" {
  description = "ARN of the scraper S3 storage bucket"
  value       = aws_s3_bucket.scraper_storage.arn
}

output "purifier_bucket_arn" {
  description = "ARN of the purifier S3 storage bucket"
  value       = aws_s3_bucket.purifier_storage.arn
}

output "processor_bucket_arn" {
  description = "ARN of the processor S3 storage bucket"
  value       = aws_s3_bucket.processor_storage.arn
}

# ============================================================================
# Secrets Manager Outputs
# ============================================================================

output "aws_config_secret_arn" {
  description = "ARN of the AWS config secret"
  value       = aws_secretsmanager_secret.aws_config.arn
}

output "queue_names_secret_arn" {
  description = "ARN of the queue names secret"
  value       = aws_secretsmanager_secret.queue_names.arn
}

output "s3_buckets_secret_arn" {
  description = "ARN of the S3 buckets secret"
  value       = aws_secretsmanager_secret.s3_buckets.arn
}

output "gemini_api_key_secret_arn" {
  description = "ARN of the Gemini API key secret"
  value       = aws_secretsmanager_secret.gemini_api_key.arn
  sensitive   = true
}

output "services_config_secret_arn" {
  description = "ARN of the services config secret"
  value       = aws_secretsmanager_secret.services_config.arn
}

# ============================================================================
# IAM Role Outputs
# ============================================================================

output "lambda_role_arn" {
  description = "ARN of the Lambda execution role (using LabRole)"
  value       = data.aws_iam_role.lab_role.arn
}

output "lambda_role_name" {
  description = "Name of the Lambda execution role (using LabRole)"
  value       = data.aws_iam_role.lab_role.name
}
