variable "project_name" {
  description = "The name of the project"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.12.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "aws" {
  region = "us-east-1"
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

variable "api_rest_name" {}
variable "scraper_name" {}
variable "processor_name" {}
variable "embedder_name" {}
variable "inserter_name" {}
variable "relational_guard_name" {}
variable "vectorial_guard_name" {}
variable "queue_name" {}
variable "vdb_name" {}
variable "relational_db_name" {}

variable "default_instance_type" {}


# Lambda Configuration Variables
variable "lambda_runtime" {
  description = "Lambda runtime for Java functions"
  type        = string
  default     = "java17"
}

variable "lambda_memory_size" {
  description = "Memory size for Lambda functions in MB"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Timeout for Lambda functions in seconds"
  type        = number
  default     = 30
}

variable "lambda_log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
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