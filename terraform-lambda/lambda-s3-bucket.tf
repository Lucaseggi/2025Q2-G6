# ============================================
# S3 Bucket for Lambda Deployment Artifacts
# ============================================

resource "aws_s3_bucket" "lambda_artifacts" {
  bucket = "${var.project_name}-lambda-artifacts-${data.aws_caller_identity.current.account_id}"

  tags = merge(var.tags, {
    Name    = "${var.project_name}-lambda-artifacts"
    Purpose = "Lambda deployment packages"
  })
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

resource "aws_s3_bucket_versioning" "lambda_artifacts" {
  bucket = aws_s3_bucket.lambda_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Upload relational-guard JAR to S3
resource "aws_s3_object" "relational_guard_jar" {
  bucket      = aws_s3_bucket.lambda_artifacts.id
  key         = "relational-guard/relational-guard-1.0.0.jar"
  source      = "${path.module}/lambda-artifacts/relational-guard-1.0.0.jar"
  source_hash = filemd5("${path.module}/lambda-artifacts/relational-guard-1.0.0.jar")

  tags = {
    Service = "relational-guard"
  }
}

# Upload vectorial-guard JAR to S3
resource "aws_s3_object" "vectorial_guard_jar" {
  bucket      = aws_s3_bucket.lambda_artifacts.id
  key         = "vectorial-guard/vectorial-guard-1.0.0.jar"
  source      = "${path.module}/lambda-artifacts/vectorial-guard-1.0.0.jar"
  source_hash = filemd5("${path.module}/lambda-artifacts/vectorial-guard-1.0.0.jar")

  tags = {
    Service = "vectorial-guard"
  }
}

# Output bucket name for reference
output "lambda_artifacts_bucket" {
  description = "S3 bucket name for Lambda artifacts"
  value       = aws_s3_bucket.lambda_artifacts.id
}
