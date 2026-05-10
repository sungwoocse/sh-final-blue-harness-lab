# ===========================================
# K3s Module Variables
# ===========================================

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs for K3s nodes"
  type        = list(string)
}

variable "key_name" {
  description = "EC2 Key Pair name"
  type        = string
}

variable "master_instance_type" {
  description = "Instance type for K3s master"
  type        = string
  default     = "m7i-flex.large"
}

variable "master_volume_size" {
  description = "Root volume size for master (GB)"
  type        = number
  default     = 50
}

variable "workers" {
  description = "Map of worker configurations"
  type = map(object({
    instance_type = string
    volume_size   = number
    role          = string
    workload      = string
    subnet_index  = number
  }))
  default = {}
}

variable "k3s_token" {
  description = "K3s cluster token for worker nodes"
  type        = string
  sensitive   = true
}

variable "ami_id" {
  description = "Specific AMI ID (empty for latest Amazon Linux 2023)"
  type        = string
  default     = ""
}

variable "allowed_ssh_cidr_blocks" {
  description = "CIDR blocks allowed to SSH"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "allocate_eip" {
  description = "Allocate Elastic IP for master"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
