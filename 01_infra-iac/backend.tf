terraform {
  backend "s3" {
    bucket         = "softbank2025-blue-tfstate"
    key            = "blue/terraform.tfstate"
    region         = "ap-northeast-2"
    dynamodb_table = "softbank2025-blue-tfstate-lock"
    encrypt        = true
  }
}
