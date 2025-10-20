terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.12.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Use existing LabRole from AWS Academy instead of creating new role
data "aws_iam_role" "lab_role" {
  name = "LabRole"
}

# Scraper Lambda
resource "aws_lambda_function" "scraper" {
  function_name = "simpla-scraper"
  role          = data.aws_iam_role.lab_role.arn
  package_type  = "Image"
  image_uri     = var.scraper_image_uri
  timeout       = 300
  memory_size   = 512

  environment {
    variables = {
      # Secrets Manager configuration (no endpoint in production)
      SECRETS_MANAGER_ENDPOINT = ""
    }
  }

  # Depends on secrets being created
  depends_on = [
    aws_secretsmanager_secret_version.aws_config,
    aws_secretsmanager_secret_version.queue_names,
    aws_secretsmanager_secret_version.s3_buckets,
    aws_secretsmanager_secret_version.services_config
  ]

  tags = {
    Name        = "simpla-scraper"
    Environment = var.environment
    Service     = "scraper"
  }
}

# Purifier Lambda (handles both SQS and API Gateway triggers)
resource "aws_lambda_function" "purifier" {
  function_name = "simpla-purifier"
  role          = data.aws_iam_role.lab_role.arn
  package_type  = "Image"
  image_uri     = var.purifier_image_uri
  timeout       = 300
  memory_size   = 1024

  environment {
    variables = {
      SECRETS_MANAGER_ENDPOINT = ""
    }
  }

  depends_on = [
    aws_secretsmanager_secret_version.aws_config,
    aws_secretsmanager_secret_version.queue_names,
    aws_secretsmanager_secret_version.s3_buckets,
    aws_secretsmanager_secret_version.gemini_api_key,
    aws_secretsmanager_secret_version.services_config
  ]

  tags = {
    Name        = "simpla-purifier"
    Environment = var.environment
    Service     = "purifier"
  }
}

# Processor Lambda (handles both SQS and API Gateway triggers)
resource "aws_lambda_function" "processor" {
  function_name = "simpla-processor"
  role          = data.aws_iam_role.lab_role.arn
  package_type  = "Image"
  image_uri     = var.processor_image_uri
  timeout       = 900  # 15 minutes for LLM processing
  memory_size   = 2048

  environment {
    variables = {
      SECRETS_MANAGER_ENDPOINT = ""
    }
  }

  depends_on = [
    aws_secretsmanager_secret_version.aws_config,
    aws_secretsmanager_secret_version.queue_names,
    aws_secretsmanager_secret_version.s3_buckets,
    aws_secretsmanager_secret_version.gemini_api_key,
    aws_secretsmanager_secret_version.services_config
  ]

  tags = {
    Name        = "simpla-processor"
    Environment = var.environment
    Service     = "processor"
  }
}

# Embedder Lambda is now defined in lambda-embedder-api.tf using the lambda-api module

# Inserter Lambda (handles SQS triggers)
resource "aws_lambda_function" "inserter" {
  function_name = "simpla-inserter"
  role          = data.aws_iam_role.lab_role.arn
  package_type  = "Image"
  image_uri     = var.inserter_image_uri
  timeout       = 300
  memory_size   = 512

  environment {
    variables = {
      SECRETS_MANAGER_ENDPOINT = ""
    }
  }

  depends_on = [
    aws_secretsmanager_secret_version.aws_config,
    aws_secretsmanager_secret_version.queue_names,
    aws_secretsmanager_secret_version.s3_buckets,
    aws_secretsmanager_secret_version.services_config
  ]

  tags = {
    Name        = "simpla-inserter"
    Environment = var.environment
    Service     = "inserter"
  }
}
