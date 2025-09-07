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
variable "scrapper_ms_name" {}
variable "processing_ms_name" {}
variable "embedding_ms_name" {}
variable "inserter_ms_name" {}
variable "queue_name" {}

variable "default_instance_type" {}

