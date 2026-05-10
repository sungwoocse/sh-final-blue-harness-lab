terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-northeast-2"

  default_tags {
    tags = {
      Project     = "Softbank2025-Cat"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }

  # kOps가 추가하는 태그 무시
  ignore_tags {
    keys = ["SubnetType"]
    key_prefixes = ["kubernetes.io/cluster/sfbank-blue"]
  }
}

# US-EAST-1 provider for CloudFront WAF (WAF for CloudFront must be in us-east-1)
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      Project     = "Softbank2025-final-blue"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
