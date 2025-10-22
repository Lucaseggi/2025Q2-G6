# ============================================
# Vectorial Guard Lambda Function
# ============================================

module "vectorial_guard" {
  source = "./modules/lambda-api"

  project_name = var.project_name
  service_name = "vectorial-guard"

  # Use S3 for deployment
  s3_bucket = aws_s3_bucket.lambda_artifacts.id
  s3_key    = aws_s3_object.vectorial_guard_jar.key

  handler         = "com.simpla.vectorial.lambda.StreamLambdaHandler::handleRequest"
  lambda_role_arn = data.aws_iam_role.lab_role.arn
  runtime         = var.lambda_runtime
  memory_size     = var.lambda_memory_size
  timeout         = var.lambda_timeout

  # VPC configuration to access OpenSearch ECS
  vpc_subnet_ids         = [aws_subnet.private_1.id]
  vpc_security_group_ids = [aws_security_group.public_sg.id, aws_security_group.vdb_sg.id]

  environment_variables = {
    VECTOR_STORE_TYPE = var.vector_store_type
    PINECONE_API_KEY  = var.pinecone_api_key
    PINECONE_INDEX    = var.pinecone_index

    # OpenSearch configuration
    # Lambda will discover the actual IP at runtime using ECS API with cluster/service names
    OPENSEARCH_HOST         = aws_instance.vector_db.private_ip
    OPENSEARCH_PORT         = var.opensearch_port
    OPENSEARCH_INDEX        = var.opensearch_index
  }

  # Depend on OpenSearch resources
  depends_on = [
    aws_security_group.private_sg,
    aws_security_group.vdb_sg,
  ]
}

# ============================================
# Outputs
# ============================================

output "vectorial_guard_lambda_function_name" {
  description = "Name of the Vectorial Guard Lambda function"
  value       = module.vectorial_guard.lambda_function_name
}

output "vectorial_guard_api_id" {
  description = "ID of the Vectorial Guard API Gateway"
  value       = module.vectorial_guard.api_id
}

output "vectorial_guard_api_url" {
  description = "Base URL of the Vectorial Guard API"
  value       = "${module.vectorial_guard.api_endpoint}/api/v1/vectorial"
}

output "vectorial_guard_endpoints" {
  description = "Available Vectorial Guard API endpoints"
  value = {
    store  = "${module.vectorial_guard.api_endpoint}/api/v1/vectorial/store"
    search = "${module.vectorial_guard.api_endpoint}/api/v1/vectorial/search"
  }
}
