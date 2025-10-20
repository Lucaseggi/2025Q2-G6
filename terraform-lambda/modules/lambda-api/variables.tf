variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
}

variable "service_name" {
  description = "Name of the service (e.g., relational-guard, vectorial-guard)"
  type        = string
}

variable "jar_path" {
  description = "Path to the JAR file for the Lambda function (used when s3_bucket is not set)"
  type        = string
  default     = null
}

variable "s3_bucket" {
  description = "S3 bucket containing the Lambda deployment package"
  type        = string
  default     = null
}

variable "s3_key" {
  description = "S3 key for the Lambda deployment package"
  type        = string
  default     = null
}

variable "handler" {
  description = "Lambda function handler"
  type        = string
}

variable "lambda_role_arn" {
  description = "ARN of the IAM role for Lambda execution"
  type        = string
}

variable "runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "java17"
}

variable "package_type" {
  description = "Lambda deployment package type (Zip or Image)"
  type        = string
  default     = "Zip"
  validation {
    condition     = contains(["Zip", "Image"], var.package_type)
    error_message = "package_type must be either 'Zip' or 'Image'"
  }
}

variable "image_uri" {
  description = "ECR image URI for Lambda function (used when package_type is Image)"
  type        = string
  default     = null
}

variable "memory_size" {
  description = "Memory size for Lambda function in MB"
  type        = number
  default     = 512
}

variable "timeout" {
  description = "Timeout for Lambda function in seconds"
  type        = number
  default     = 30
}

variable "environment_variables" {
  description = "Environment variables for the Lambda function"
  type        = map(string)
  default     = {}
}
