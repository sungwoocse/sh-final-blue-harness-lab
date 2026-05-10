variable "vpc_cidr" {
  type        = string
  description = "VPC CIDR"
  default     = "10.180.0.0/20"
}

variable "name" {
  type        = string
  description = "리소스 접두사"
  default     = "ticket"
}

variable "azs" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["ap-northeast-2a", "ap-northeast-2c"]
}

variable "public_cidrs" {
  description = "List of CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.180.0.0/24", "10.180.1.0/24"]
}

variable "private_app_cidrs" {
  description = "List of CIDR blocks for private application subnets"
  type        = list(string)
  default     = ["10.180.4.0/22", "10.180.8.0/22"]
}

variable "private_db_cidrs" {
  description = "List of CIDR blocks for private database subnets"
  type        = list(string)
  default     = ["10.180.2.0/24", "10.180.3.0/24"]
}

variable "region" {
  type        = string
  description = "AWS region"
  default     = "ap-northeast-2"
}
