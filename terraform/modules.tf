module "lambda_relational_guard" {
  source = "./lambda"

  project_name = var.project_name

  # Lambda configuration
  lambda_runtime            = var.lambda_runtime
  lambda_memory_size        = var.lambda_memory_size
  lambda_timeout            = var.lambda_timeout
  lambda_log_retention_days = var.lambda_log_retention_days

  # Database configuration
  postgres_host     = var.postgres_host
  postgres_port     = var.postgres_port
  postgres_user     = var.postgres_user
  postgres_db       = var.postgres_db
  postgres_password = var.postgres_password
}
