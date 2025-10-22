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

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets. Set to true for initial setup, false after deployment."
  type        = bool
  default     = false
}

variable "enable_bastion" {
  description = "Enable bastion host for SSH access to private instances. Set to true when needed, false to save costs."
  type        = bool
  default     = false
}

variable "vpc_tags" {
  description = "VPC Tags"
  type        = map(string)
  default     = {}
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.1.0.0/16"
}

variable "public_subnet_1_cidr" {
  description = "CIDR block for the Public Subnet 1"
  type        = string
  default     = "10.1.1.0/24"
}

variable "public_subnet_2_cidr" {
  description = "CIDR block for the Public Subnet 2"
  type        = string
  default     = "10.1.2.0/24"
}

variable "private_subnet_1_cidr" {
  description = "CIDR block for the Private Subnet 1"
  type        = string
  default     = "10.1.3.0/24"
}

variable "private_subnet_2_cidr" {
  description = "CIDR block for the Private Subnet 2"
  type        = string
  default     = "10.1.4.0/24"
}

variable "private_subnet_3_cidr" {
  description = "CIDR block for the Private Subnet 3"
  type        = string
  default     = "10.1.5.0/24"
}

variable "private_subnet_4_cidr" {
  description = "CIDR block for the Private Subnet 4"
  type        = string
  default     = "10.1.6.0/24"
}

variable "api_sg_name" {}
variable "priv_sg_name" {}
variable "vdb_sg_name" {}

variable "vdb_name" {}

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

variable "opensearch_image_uri" {
  description = "ECR image URI for OpenSearch ECS"
  type        = string
}

variable "inserter_image_uri" {
  description = "ECR image URI for inserter Lambda"
  type        = string
}
variable "db_seeder_image_uri" {
  description = "ECR image URI for relational db seeder Lambda"
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
  default = {
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

variable "rds_engine"{
  type=string
  default="postgres"
}

variable "rds_engine_version"{
  type=string
  default="16"
}

variable "rds_instance_class"{
  type=string
  default="db.t3.medium"
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

# OpenSearch ECS Fargate Configuration
variable "opensearch_cpu" {
  description = "CPU units for OpenSearch Fargate task (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "opensearch_memory" {
  description = "Memory for OpenSearch Fargate task in MB"
  type        = number
  default     = 2048 # 2GB RAM
}