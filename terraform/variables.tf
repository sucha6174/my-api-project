variable "aws_region" {
  description = "The target AWS region for infrastructure deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "The deployment environment tier (e.g., staging, production)"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Naming prefix applied to all managed cloud resources"
  type        = string
  default     = "my-api"
}

variable "db_name" {
  description = "The relational database name created on RDS"
  type        = string
  default     = "mydatabase"
}

variable "db_username" {
  description = "The database administrator username"
  type        = string
  default     = "dbadmin"
}
