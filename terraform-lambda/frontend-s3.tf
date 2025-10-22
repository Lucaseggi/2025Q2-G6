# ============================================
# Frontend S3 Static Website Hosting
# ============================================
# This creates an S3 bucket configured for static website hosting
# without CloudFront (for environments with limited AWS permissions)

# Generate a random suffix to ensure globally unique bucket name
resource "random_id" "frontend_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "frontend" {
  bucket = "${var.project_name}-frontend-${var.environment}-${random_id.frontend_suffix.hex}"

  tags = {
    Name        = "${var.project_name}-frontend"
    Environment = var.environment
    Service     = "frontend"
  }
}

# Enable static website hosting
resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"  # For SPA routing - all 404s redirect to index.html
  }
}

# Disable block public access settings (required for public website)
resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# Bucket policy to allow public read access
resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  # Ensure public access block is disabled first
  depends_on = [aws_s3_bucket_public_access_block.frontend]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.frontend.arn}/*"
      }
    ]
  })
}

# Optional: Enable versioning for rollback capability
resource "aws_s3_bucket_versioning" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Optional: CORS configuration (if API and frontend are on different domains)
resource "aws_s3_bucket_cors_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# ============================================
# Outputs
# ============================================

output "frontend_bucket_name" {
  description = "Name of the S3 bucket hosting the frontend"
  value       = aws_s3_bucket.frontend.id
}

output "frontend_bucket_arn" {
  description = "ARN of the S3 bucket hosting the frontend"
  value       = aws_s3_bucket.frontend.arn
}

output "frontend_website_endpoint" {
  description = "S3 website endpoint (HTTP only)"
  value       = aws_s3_bucket_website_configuration.frontend.website_endpoint
}

output "frontend_website_url" {
  description = "Full URL to access the frontend website"
  value       = "http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}"
}

output "frontend_s3_url" {
  description = "S3 bucket URL (not website endpoint)"
  value       = "https://${aws_s3_bucket.frontend.bucket_regional_domain_name}"
}
