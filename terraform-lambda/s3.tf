# S3 Buckets for Simpla Pipeline
# Creates cache/storage buckets for scraper, purifier, and processor
resource "random_string" "bucket_suffix" {
  length  = 8
  upper   = false
  special = false
}
# Scraper Storage Bucket
resource "aws_s3_bucket" "scraper_storage" {
  bucket = "${var.scraper_bucket_name}-${random_string.bucket_suffix.result}"

  tags = {
    Name        = "simpla-scraper-storage"
    Environment = var.environment
    Service     = "scraper"
    Purpose     = "Cache scraped HTML and raw responses"
  }
}

# Enable versioning for scraper bucket
resource "aws_s3_bucket_versioning" "scraper_storage" {
  bucket = aws_s3_bucket.scraper_storage.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption for scraper bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "scraper_storage" {
  bucket = aws_s3_bucket.scraper_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy for scraper bucket (optional - clean old data)
resource "aws_s3_bucket_lifecycle_configuration" "scraper_storage" {
  bucket = aws_s3_bucket.scraper_storage.id

  rule {
    id     = "expire-old-scrapes"
    status = "Enabled"

    expiration {
      days = 90  # Keep scraped data for 90 days
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# Purifier Storage Bucket
resource "aws_s3_bucket" "purifier_storage" {
  bucket = "${var.purifier_bucket_name}-${random_string.bucket_suffix.result}"

  tags = {
    Name        = "simpla-purifier-storage"
    Environment = var.environment
    Service     = "purifier"
    Purpose     = "Cache purified/cleaned text"
  }
}

# Enable versioning for purifier bucket
resource "aws_s3_bucket_versioning" "purifier_storage" {
  bucket = aws_s3_bucket.purifier_storage.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption for purifier bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "purifier_storage" {
  bucket = aws_s3_bucket.purifier_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy for purifier bucket
resource "aws_s3_bucket_lifecycle_configuration" "purifier_storage" {
  bucket = aws_s3_bucket.purifier_storage.id

  rule {
    id     = "expire-old-purified"
    status = "Enabled"

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# Processor Storage Bucket
resource "aws_s3_bucket" "processor_storage" {
  bucket = "${var.processor_bucket_name}-${random_string.bucket_suffix.result}"

  tags = {
    Name        = "simpla-processor-storage"
    Environment = var.environment
    Service     = "processor"
    Purpose     = "Cache LLM-structured data"
  }
}

# Enable versioning for processor bucket
resource "aws_s3_bucket_versioning" "processor_storage" {
  bucket = aws_s3_bucket.processor_storage.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption for processor bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "processor_storage" {
  bucket = aws_s3_bucket.processor_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy for processor bucket
resource "aws_s3_bucket_lifecycle_configuration" "processor_storage" {
  bucket = aws_s3_bucket.processor_storage.id

  rule {
    id     = "expire-old-processed"
    status = "Enabled"

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# Block public access for all buckets
resource "aws_s3_bucket_public_access_block" "scraper_storage" {
  bucket = aws_s3_bucket.scraper_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "purifier_storage" {
  bucket = aws_s3_bucket.purifier_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "processor_storage" {
  bucket = aws_s3_bucket.processor_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
