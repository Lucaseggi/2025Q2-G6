# ============================================
# Answer Generator Lambda Function with API Gateway
# ============================================

module "answer_generator_api" {
  source = "./modules/lambda-api"

  project_name     = var.project_name
  service_name     = "answer-generator"

  # Use Docker image deployment
  package_type     = "Image"
  image_uri        = var.answer_generator_image_uri

  # Handler not needed for Docker images (entrypoint in Dockerfile)
  handler          = ""
  lambda_role_arn  = data.aws_iam_role.lab_role.arn
  memory_size      = 1024
  timeout          = 300

  environment_variables = {
    EMBEDDER_API_HOST    = module.embedder_api.api_endpoint
    VECTORIAL_API_HOST   = module.vectorial_guard.api_endpoint
    RELATIONAL_API_HOST  = module.relational_guard.api_endpoint
    DEFAULT_SEARCH_LIMIT = "5"
  }

  # Depends on secrets being created and guard services
  depends_on = [
    aws_secretsmanager_secret_version.aws_config,
    aws_secretsmanager_secret_version.queue_names,
    aws_secretsmanager_secret_version.s3_buckets,
    aws_secretsmanager_secret_version.gemini_api_key,
    aws_secretsmanager_secret_version.services_config,
    aws_secretsmanager_secret_version.guard_endpoints,
    module.embedder_api,
    module.vectorial_guard,
    module.relational_guard
  ]
}

# ============================================
# Outputs
# ============================================

output "answer_generator_api_lambda_function_name" {
  description = "Name of the Answer Generator API Lambda function"
  value       = module.answer_generator_api.lambda_function_name
}

output "answer_generator_api_id" {
  description = "ID of the Answer Generator API Gateway"
  value       = module.answer_generator_api.api_id
}

output "answer_generator_api_url" {
  description = "Base URL of the Answer Generator API"
  value       = module.answer_generator_api.api_endpoint
}

output "answer_generator_endpoints" {
  description = "Available Answer Generator API endpoints"
  value = {
    health   = "${module.answer_generator_api.api_endpoint}/health"
    question = "${module.answer_generator_api.api_endpoint}/question"
  }
}
