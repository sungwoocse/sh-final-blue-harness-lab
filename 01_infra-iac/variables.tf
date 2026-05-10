# ===========================================
# Project Configuration
# ===========================================

variable "project_name" {
  description = "프로젝트 이름 (리소스 접두사)"
  type        = string
  default     = "blue-final"
}

variable "environment" {
  description = "환경 (dev, staging, prod)"
  type        = string
  default     = "dev"
}

# ===========================================
# VPC Configuration
# ===========================================

variable "vpc_cidr" {
  description = "VPC CIDR 블록"
  type        = string
  default     = "10.180.0.0/20"
}

variable "availability_zones" {
  description = "사용할 가용 영역 리스트"
  type        = list(string)
  default     = ["ap-northeast-2a", "ap-northeast-2c"]
}

variable "public_subnet_cidrs" {
  description = "Public 서브넷 CIDR 리스트"
  type        = list(string)
  default     = ["10.180.0.0/24", "10.180.1.0/24"]
}

variable "private_app_subnet_cidrs" {
  description = "Private App 서브넷 CIDR 리스트"
  type        = list(string)
  default     = ["10.180.4.0/22", "10.180.8.0/22"]
}

variable "private_db_subnet_cidrs" {
  description = "Private DB 서브넷 CIDR 리스트"
  type        = list(string)
  default     = ["10.180.2.0/24", "10.180.3.0/24"]
}

# ===========================================
# Domain Configuration
# ===========================================

variable "alb_certificate_arn" {
  description = "ACM certificate ARN for ALB HTTPS listener (ap-northeast-2)"
  type        = string
  default     = "arn:aws:acm:ap-northeast-2:217350599014:certificate/ead557d2-eee7-4b32-8730-43ee48076edc"
}

# ===========================================
# CloudFront Configuration
# ===========================================

variable "create_cloudfront" {
  description = "Create CloudFront distribution"
  type        = bool
  default     = true
}

variable "cloudfront_certificate_arn" {
  description = "ACM certificate ARN for CloudFront (must be in us-east-1)"
  type        = string
  default     = "arn:aws:acm:us-east-1:217350599014:certificate/d8fc1fde-3b6f-45ec-9c4a-5738ab96a22f"
}

variable "frontend_s3_bucket_name" {
  description = "S3 bucket name for frontend static files"
  type        = string
  default     = "eunha-icu-frontend"
}

# ===========================================
# WAF Configuration
# ===========================================

variable "create_waf" {
  description = "Create WAF Web ACL for CloudFront"
  type        = bool
  default     = true
}

variable "waf_rate_limit" {
  description = "Maximum number of requests per 5 minutes from a single IP"
  type        = number
  default     = 2000
}

variable "waf_enable_cloudwatch_metrics" {
  description = "Enable CloudWatch metrics for WAF"
  type        = bool
  default     = false
}

variable "waf_enable_sampled_requests" {
  description = "Enable sampling of requests for WAF"
  type        = bool
  default     = false
}

# ===========================================
# Bastion Host Configuration
# ===========================================

variable "create_bastion" {
  description = "Whether to create Bastion Host"
  type        = bool
  default     = false  # 비활성화됨 - K3s 노드로 SSH 접속 가능
}

variable "bastion_instance_type" {
  description = "EC2 instance type for Bastion Host"
  type        = string
  default     = "t3.micro"
}

variable "bastion_allocate_eip" {
  description = "Whether to allocate Elastic IP for Bastion"
  type        = bool
  default     = true
}

variable "bastion_root_volume_size" {
  description = "Root volume size for Bastion (GB)"
  type        = number
  default     = 30
}

variable "bastion_ami_id" {
  description = "Specific AMI ID for Bastion Host (empty string to use latest Amazon Linux 2023)"
  type        = string
  default     = ""
}

variable "bastion_allowed_cidr_blocks" {
  description = "CIDR blocks allowed to SSH into Bastion"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "bastion_key_name" {
  description = "Existing EC2 Key Pair name for Bastion (if empty, creates new key)"
  type        = string
  default     = "blue-key"
}

# ===========================================
# K3s Cluster Configuration
# ===========================================

variable "create_k3s" {
  description = "Whether to create K3s cluster"
  type        = bool
  default     = false
}

variable "k3s_key_name" {
  description = "EC2 Key Pair name for K3s nodes"
  type        = string
  default     = "blue-key"
}

variable "k3s_master_instance_type" {
  description = "Instance type for K3s master"
  type        = string
  default     = "m7i-flex.large"
}

variable "k3s_master_volume_size" {
  description = "Root volume size for K3s master (GB)"
  type        = number
  default     = 50
}

variable "k3s_worker_instance_type" {
  description = "Instance type for K3s workers"
  type        = string
  default     = "m7i-flex.large"
}

variable "k3s_worker_volume_size" {
  description = "Root volume size for K3s workers (GB)"
  type        = number
  default     = 50
}

variable "k3s_token" {
  description = "K3s cluster token (generate with: openssl rand -hex 32)"
  type        = string
  sensitive   = true
  default     = "default-k3s-token-change-me"
}

variable "k3s_allocate_eip" {
  description = "Allocate Elastic IP for K3s master"
  type        = bool
  default     = true
}

variable "k3s_allowed_ssh_cidr_blocks" {
  description = "CIDR blocks allowed to SSH into K3s nodes"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
