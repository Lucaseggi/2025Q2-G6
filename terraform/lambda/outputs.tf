# Lambda and API Gateway Outputs
output "relational_guard_api_url" {
  description = "API Gateway base URL for Relational Guard Lambda function"
  value       = "${aws_api_gateway_stage.prod.invoke_url}/api/v1/relational"
}

output "relational_guard_api_id" {
  description = "API Gateway REST API ID"
  value       = aws_api_gateway_rest_api.relational_guard.id
}

output "relational_guard_lambda_function_name" {
  description = "Name of the Relational Guard Lambda function"
  value       = aws_lambda_function.relational_guard.function_name
}

output "relational_guard_endpoints" {
  description = "All API endpoints for Relational Guard"
  value = {
    store                     = "${aws_api_gateway_stage.prod.invoke_url}/api/v1/relational/store"
    reconstruct_by_infoleg_id = "${aws_api_gateway_stage.prod.invoke_url}/api/v1/relational/reconstruct?infoleg_id=INFOLEG_ID"
    reconstruct_by_id         = "${aws_api_gateway_stage.prod.invoke_url}/api/v1/relational/reconstruct/ID"
    batch                     = "${aws_api_gateway_stage.prod.invoke_url}/api/v1/relational/batch"
  }
}
