# ===========================================
# Security Groups Variables
# ===========================================

variable "name_prefix" {
  description = "Prefix for security group names"
  type        = string
  default     = "cat"
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "create_rds_sg" {
  description = "Whether to create RDS security group"
  type        = bool
  default     = false
}

variable "create_bastion_sg" {
  description = "Whether to create Bastion security group"
  type        = bool
  default     = false
}

variable "bastion_allowed_cidr_blocks" {
  description = "CIDR blocks allowed to SSH into Bastion"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "tags" {
  description = "A map of tags to assign to resources"
  type        = map(string)
  default     = {}
}
