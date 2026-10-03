terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  # Production S3 remote state backend configuration template:
  # backend "s3" {
  #   bucket         = "my-api-terraform-state-bucket"
  #   key            = "state/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "my-api-terraform-locks"
  # }
}

provider "aws" {
  region = var.aws_region
}
