# ===========================================
# CloudFront Variables (S3 Frontend Only)
# ===========================================

variable "name_prefix" {
  description = "Prefix for CloudFront resources"
  type        = string
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for frontend static files"
  type        = string
}

variable "price_class" {
  description = "CloudFront price class"
  type        = string
  default     = "PriceClass_100"
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for custom domain (must be in us-east-1)"
  type        = string
  default     = ""
}

variable "aliases" {
  description = "Custom domain names (CNAMEs) for CloudFront distribution"
  type        = list(string)
  default     = []
}

variable "web_acl_id" {
  description = "WAF Web ACL ARN to associate with CloudFront"
  type        = string
  default     = ""
}

variable "cors_allowed_origins" {
  description = "List of allowed origins for CORS"
  type        = list(string)
  default     = ["*"]
}

variable "tags" {
  description = "A map of tags to assign to resources"
  type        = map(string)
  default     = {}
}
