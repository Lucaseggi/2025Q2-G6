# ============================================
# Reusable Lambda + API Gateway Module
# ============================================
# This module creates a Lambda function with API Gateway REST API
# Designed for Spring Boot applications packaged with maven-shade-plugin

resource "aws_lambda_function" "this" {
  function_name    = "${var.project_name}-${var.service_name}"
  role            = var.lambda_role_arn
  memory_size     = var.memory_size
  timeout         = var.timeout

  # Package type: either Image (Docker) or Zip (JAR/code)
  package_type = var.package_type

  # For Docker images
  image_uri = var.package_type == "Image" ? var.image_uri : null

  # For Zip packages (JAR files)
  filename         = var.package_type == "Zip" && var.s3_bucket == null ? var.jar_path : null
  s3_bucket        = var.package_type == "Zip" ? var.s3_bucket : null
  s3_key           = var.package_type == "Zip" ? var.s3_key : null
  source_code_hash = var.package_type == "Zip" && var.s3_bucket == null && var.jar_path != null ? filebase64sha256(var.jar_path) : null

  # Handler and runtime only for Zip packages
  handler         = var.package_type == "Zip" ? var.handler : null
  runtime         = var.package_type == "Zip" ? var.runtime : null

  environment {
    variables = var.environment_variables
  }

  lifecycle {
    create_before_destroy = false
  }

  timeouts {
    create = "5m"
    update = "5m"
  }
}

# ============================================
# API Gateway
# ============================================

resource "aws_api_gateway_rest_api" "this" {
  name = "${var.project_name}-${var.service_name}-api"
}

resource "aws_api_gateway_resource" "proxy" {
  rest_api_id = aws_api_gateway_rest_api.this.id
  parent_id   = aws_api_gateway_rest_api.this.root_resource_id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "proxy" {
  rest_api_id   = aws_api_gateway_rest_api.this.id
  resource_id   = aws_api_gateway_resource.proxy.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "proxy" {
  rest_api_id             = aws_api_gateway_rest_api.this.id
  resource_id             = aws_api_gateway_resource.proxy.id
  http_method             = aws_api_gateway_method.proxy.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.this.invoke_arn
}

resource "aws_api_gateway_method" "proxy_root" {
  rest_api_id   = aws_api_gateway_rest_api.this.id
  resource_id   = aws_api_gateway_rest_api.this.root_resource_id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "proxy_root" {
  rest_api_id             = aws_api_gateway_rest_api.this.id
  resource_id             = aws_api_gateway_rest_api.this.root_resource_id
  http_method             = aws_api_gateway_method.proxy_root.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.this.invoke_arn
}

resource "aws_api_gateway_deployment" "this" {
  rest_api_id = aws_api_gateway_rest_api.this.id

  depends_on = [
    aws_api_gateway_integration.proxy,
    aws_api_gateway_integration.proxy_root
  ]
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.this.id
  rest_api_id   = aws_api_gateway_rest_api.this.id
  stage_name    = "prod"
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.this.execution_arn}/*/*"
}
