variable "project_name" {
  description = "The name of the project"
  type        = string
}

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
variable "postgres_host" {
  description = "PostgreSQL database host"
  type        = string
}

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
