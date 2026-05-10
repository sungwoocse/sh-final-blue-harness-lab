# ===========================================
# ALB Variables
# ===========================================

variable "name_prefix" {
  description = "Prefix for ALB resources"
  type        = string
  default     = "cat"
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs"
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "Security group ID for ALB"
  type        = string
}

variable "tags" {
  description = "A map of tags to assign to resources"
  type        = map(string)
  default     = {}
}
