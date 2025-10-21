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
  depends_on       = [module.rds]

  environment_variables = {
    POSTGRES_HOST     = module.rds.db_instance_address
    POSTGRES_PORT     = var.postgres_port
    POSTGRES_DB       = var.postgres_db
    POSTGRES_USER     = var.postgres_user
    POSTGRES_PASSWORD = var.postgres_password
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
