# ===========================================
# WAF Variables
# ===========================================

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "rate_limit" {
  description = "Maximum number of requests per 5 minutes from a single IP"
  type        = number
  default     = 2000
}

variable "enable_cloudwatch_metrics" {
  description = "Enable CloudWatch metrics for WAF"
  type        = bool
  default     = false
}

variable "enable_sampled_requests" {
  description = "Enable sampling of requests for WAF"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
