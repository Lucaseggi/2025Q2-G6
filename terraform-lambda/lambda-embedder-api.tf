# ============================================
# Embedder Lambda Function with API Gateway
# ============================================

module "embedder_api" {
  source = "./modules/lambda-api"

  project_name     = var.project_name
  service_name     = "embedder"

  # Use Docker image deployment
  package_type     = "Image"
  image_uri        = var.embedder_image_uri

  # Handler not needed for Docker images (entrypoint in Dockerfile)
  handler          = ""
  lambda_role_arn  = data.aws_iam_role.lab_role.arn
  memory_size      = 1024
  timeout          = 300

  environment_variables = {
    SECRETS_MANAGER_ENDPOINT = ""
  }

  # Depends on secrets being created
  depends_on = [
    aws_secretsmanager_secret_version.aws_config,
    aws_secretsmanager_secret_version.queue_names,
    aws_secretsmanager_secret_version.s3_buckets,
    aws_secretsmanager_secret_version.gemini_api_key,
    aws_secretsmanager_secret_version.services_config
  ]
}

# ============================================
# Outputs
# ============================================

output "embedder_api_lambda_function_name" {
  description = "Name of the Embedder API Lambda function"
  value       = module.embedder_api.lambda_function_name
}

output "embedder_api_id" {
  description = "ID of the Embedder API Gateway"
  value       = module.embedder_api.api_id
}

output "embedder_api_url" {
  description = "Base URL of the Embedder API"
  value       = module.embedder_api.api_endpoint
}

output "embedder_endpoints" {
  description = "Available Embedder API endpoints"
  value = {
    health = "${module.embedder_api.api_endpoint}/health"
    embed  = "${module.embedder_api.api_endpoint}/embed"
  }
}
