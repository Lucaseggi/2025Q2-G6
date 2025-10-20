variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

# ECR Image URIs
variable "scraper_image_uri" {
  description = "ECR image URI for scraper Lambda"
  type        = string
}

variable "purifier_image_uri" {
  description = "ECR image URI for purifier Lambda"
  type        = string
}

variable "processor_image_uri" {
  description = "ECR image URI for processor Lambda"
  type        = string
}

variable "embedder_image_uri" {
  description = "ECR image URI for embedder Lambda"
  type        = string
}

variable "answer_generator_image_uri" {
  description = "ECR image URI for answer generator Lambda"
  type        = string
}

variable "inserter_image_uri" {
  description = "ECR image URI for inserter Lambda"
  type        = string
}

# SQS Queue Names
variable "purifying_queue_name" {
  description = "Name of the purifying SQS queue"
  type        = string
  default     = "purifying"
}

variable "processing_queue_name" {
  description = "Name of the processing SQS queue"
  type        = string
  default     = "processing"
}

variable "embedding_queue_name" {
  description = "Name of the embedding SQS queue"
  type        = string
  default     = "embedding"
}

variable "inserting_queue_name" {
  description = "Name of the inserting SQS queue"
  type        = string
  default     = "inserting"
}

# S3 Bucket Names
variable "scraper_bucket_name" {
  description = "Name of the scraper S3 storage bucket"
  type        = string
  default     = "simpla-scraper-storage"
}

variable "purifier_bucket_name" {
  description = "Name of the purifier S3 storage bucket"
  type        = string
  default     = "simpla-purifier-storage"
}

variable "processor_bucket_name" {
  description = "Name of the processor S3 storage bucket"
  type        = string
  default     = "simpla-processor-storage"
}

# API Keys and Configuration
variable "gemini_api_key" {
  description = "Gemini API key for LLM services"
  type        = string
  sensitive   = true
}

variable "opensearch_endpoint" {
  description = "OpenSearch endpoint URL (optional for now)"
  type        = string
  default     = "http://localhost:9200"  # Placeholder for future use
}

variable "storage_client_type" {
  description = "Storage client type for inserter (rest or grpc)"
  type        = string
  default     = "rest"
}

# Guard Lambda Variables
variable "project_name" {
  description = "Project name for guard services"
  type        = string
  default     = "simpla"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {
    Project = "simpla"
  }
}

variable "lambda_runtime" {
  description = "Lambda runtime for Java guard functions"
  type        = string
  default     = "java17"
}

variable "lambda_memory_size" {
  description = "Memory size for guard Lambda functions in MB"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Timeout for guard Lambda functions in seconds"
  type        = number
  default     = 30
}

# Database Configuration Variables
variable "postgres_host" {}

variable "postgres_port" {
  description = "PostgreSQL database port"
  type        = string
  default     = "5432"
}

variable "postgres_db" {
  description = "PostgreSQL database name"
  type        = string
  default     = "postgres"
}

variable "postgres_user" {
  description = "PostgreSQL database user"
  type        = string
  default     = "postgres"
}

variable "postgres_password" {
  description = "PostgreSQL database password"
  type        = string
  sensitive   = true
}

# Database and Vector Store Endpoints
variable "vector_store_type" {
  description = "Type of vector store to use (pinecone or opensearch)"
  type        = string
  default     = "pinecone"
}

variable "pinecone_api_key" {
  description = "Pinecone API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "pinecone_index" {
  description = "Pinecone index name"
  type        = string
  default     = "simpla-vectors"
}

variable "opensearch_host" {
  description = "OpenSearch host URL"
  type        = string
  default     = ""
}

variable "opensearch_port" {
  description = "OpenSearch port"
  type        = string
  default     = "443"
}

variable "opensearch_index" {
  description = "OpenSearch index name"
  type        = string
  default     = "simpla-vectors"
}