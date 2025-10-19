output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.this.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.this.arn
}

output "lambda_invoke_arn" {
  description = "Invoke ARN of the Lambda function"
  value       = aws_lambda_function.this.invoke_arn
}

output "api_id" {
  description = "ID of the API Gateway REST API"
  value       = aws_api_gateway_rest_api.this.id
}

output "api_endpoint" {
  description = "Base URL of the API Gateway"
  value       = aws_api_gateway_stage.prod.invoke_url
}

output "api_execution_arn" {
  description = "Execution ARN of the API Gateway"
  value       = aws_api_gateway_rest_api.this.execution_arn
}
