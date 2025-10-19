data "aws_iam_role" "lab_role" {
  name = "LabRole"
}

# ============================================
# Lambda Function
# ============================================
# Note: The JAR file from maven-shade-plugin is already a valid Lambda deployment package.
# AWS Lambda accepts JAR files directly for Java runtimes - no need to wrap in a ZIP.

resource "aws_lambda_function" "relational_guard" {
  filename         = "${path.module}/lambda-artifacts/relational-guard-1.0.0.jar"
  function_name    = "${var.project_name}-relational-guard"
  role            = data.aws_iam_role.lab_role.arn
  handler         = "com.simpla.relational.lambda.StreamLambdaHandler::handleRequest"
  source_code_hash = filebase64sha256("${path.module}/lambda-artifacts/relational-guard-1.0.0.jar")
  runtime         = var.lambda_runtime
  memory_size     = var.lambda_memory_size
  timeout         = var.lambda_timeout

  environment {
    variables = {
      POSTGRES_HOST     = var.postgres_host
      POSTGRES_PORT     = var.postgres_port
      POSTGRES_DB       = var.postgres_db
      POSTGRES_USER     = var.postgres_user
      POSTGRES_PASSWORD = var.postgres_password
    }
  }
}

# ============================================
# API Gateway
# ============================================

resource "aws_api_gateway_rest_api" "relational_guard" {
  name = "${var.project_name}-relational-guard-api"
}

resource "aws_api_gateway_resource" "proxy" {
  rest_api_id = aws_api_gateway_rest_api.relational_guard.id
  parent_id   = aws_api_gateway_rest_api.relational_guard.root_resource_id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "proxy" {
  rest_api_id   = aws_api_gateway_rest_api.relational_guard.id
  resource_id   = aws_api_gateway_resource.proxy.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "proxy" {
  rest_api_id             = aws_api_gateway_rest_api.relational_guard.id
  resource_id             = aws_api_gateway_resource.proxy.id
  http_method             = aws_api_gateway_method.proxy.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.relational_guard.invoke_arn
}

resource "aws_api_gateway_method" "proxy_root" {
  rest_api_id   = aws_api_gateway_rest_api.relational_guard.id
  resource_id   = aws_api_gateway_rest_api.relational_guard.root_resource_id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "proxy_root" {
  rest_api_id             = aws_api_gateway_rest_api.relational_guard.id
  resource_id             = aws_api_gateway_rest_api.relational_guard.root_resource_id
  http_method             = aws_api_gateway_method.proxy_root.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.relational_guard.invoke_arn
}

resource "aws_api_gateway_deployment" "relational_guard" {
  rest_api_id = aws_api_gateway_rest_api.relational_guard.id

  depends_on = [
    aws_api_gateway_integration.proxy,
    aws_api_gateway_integration.proxy_root
  ]
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.relational_guard.id
  rest_api_id   = aws_api_gateway_rest_api.relational_guard.id
  stage_name    = "prod"
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.relational_guard.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.relational_guard.execution_arn}/*/*"
}
