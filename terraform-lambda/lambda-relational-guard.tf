# ============================================
# Relational Guard Lambda Function
# ============================================

module "relational_guard" {
  source = "./modules/lambda-api"

  project_name     = var.project_name
  service_name     = "relational-guard"

  # Use S3 for deployment
  s3_bucket        = aws_s3_bucket.lambda_artifacts.id
  s3_key           = aws_s3_object.relational_guard_jar.key

  handler          = "com.simpla.relational.lambda.StreamLambdaHandler::handleRequest"
  lambda_role_arn  = data.aws_iam_role.lab_role.arn
  runtime          = var.lambda_runtime
  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout

  environment_variables = {
    # PostgreSQL Configuration (temporary - will move to Secrets Manager)
    POSTGRES_DB       = "simpla_rag"
    POSTGRES_USER     = "postgres"
    POSTGRES_PASSWORD = "postgres123"
    POSTGRES_HOST     = var.postgres_host
    POSTGRES_PORT     = "5432"
  }
}

# ============================================
# Outputs
# ============================================

output "relational_guard_lambda_function_name" {
  description = "Name of the Relational Guard Lambda function"
  value       = module.relational_guard.lambda_function_name
}

output "relational_guard_api_id" {
  description = "ID of the Relational Guard API Gateway"
  value       = module.relational_guard.api_id
}

output "relational_guard_api_url" {
  description = "Base URL of the Relational Guard API"
  value       = "${module.relational_guard.api_endpoint}/api/v1/relational"
}

output "relational_guard_endpoints" {
  description = "Available Relational Guard API endpoints"
  value = {
    store                     = "${module.relational_guard.api_endpoint}/api/v1/relational/store"
    batch                     = "${module.relational_guard.api_endpoint}/api/v1/relational/batch"
    reconstruct_by_id         = "${module.relational_guard.api_endpoint}/api/v1/relational/reconstruct/ID"
    reconstruct_by_infoleg_id = "${module.relational_guard.api_endpoint}/api/v1/relational/reconstruct?infoleg_id=INFOLEG_ID"
  }
}
