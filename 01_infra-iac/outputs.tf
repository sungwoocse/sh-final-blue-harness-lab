# ===========================================
# VPC Outputs
# ===========================================

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = module.vpc.vpc_cidr
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnet
}

output "private_app_subnet_ids" {
  description = "Private app subnet IDs"
  value       = module.vpc.app_subnet
}

output "private_db_subnet_ids" {
  description = "Private DB subnet IDs"
  value       = module.vpc.db_subnet
}

# ===========================================
# ECR Outputs
# ===========================================

output "ecr_repositories" {
  description = "Map of all ECR repositories"
  value       = module.ecr.ecr_repositories
}

# ===========================================
# Security Groups Outputs
# ===========================================

output "alb_security_group_id" {
  description = "ALB Security Group ID"
  value       = module.security_groups.alb_sg_id
}

output "ecs_tasks_security_group_id" {
  description = "ECS Tasks Security Group ID"
  value       = module.security_groups.ecs_tasks_sg_id
}

# ===========================================
# ALB Outputs
# ===========================================

output "alb_arn" {
  description = "ALB ARN"
  value       = module.alb.alb_arn
}

output "alb_dns_name" {
  description = "ALB DNS Name"
  value       = module.alb.alb_dns_name
}

output "alb_default_target_group_arn" {
  description = "ALB Default Target Group ARN"
  value       = module.alb.default_target_group_arn
}

output "alb_https_listener_arn" {
  description = "ALB HTTPS Listener ARN"
  value       = module.alb.https_listener_arn
}

# ===========================================
# CloudFront Outputs
# ===========================================

output "cloudfront_id" {
  description = "CloudFront Distribution ID"
  value       = var.create_cloudfront ? module.cloudfront[0].cloudfront_id : null
}

output "cloudfront_domain_name" {
  description = "CloudFront Distribution Domain Name"
  value       = var.create_cloudfront ? module.cloudfront[0].cloudfront_domain_name : null
}

output "cloudfront_hosted_zone_id" {
  description = "CloudFront Distribution Hosted Zone ID"
  value       = var.create_cloudfront ? module.cloudfront[0].cloudfront_hosted_zone_id : null
}

output "cloudfront_status" {
  description = "CloudFront Distribution Status"
  value       = var.create_cloudfront ? module.cloudfront[0].cloudfront_status : null
}

# ===========================================
# S3 Frontend Outputs
# ===========================================

output "frontend_s3_bucket_id" {
  description = "Frontend S3 bucket ID"
  value       = var.create_cloudfront ? module.cloudfront[0].s3_bucket_id : null
}

output "frontend_s3_bucket_arn" {
  description = "Frontend S3 bucket ARN"
  value       = var.create_cloudfront ? module.cloudfront[0].s3_bucket_arn : null
}

output "frontend_s3_bucket_domain_name" {
  description = "Frontend S3 bucket domain name"
  value       = var.create_cloudfront ? module.cloudfront[0].s3_bucket_domain_name : null
}

# ===========================================
# WAF Outputs
# ===========================================

output "waf_web_acl_id" {
  description = "WAF Web ACL ID"
  value       = var.create_waf ? module.waf[0].web_acl_id : null
}

output "waf_web_acl_arn" {
  description = "WAF Web ACL ARN"
  value       = var.create_waf ? module.waf[0].web_acl_arn : null
}

output "waf_web_acl_name" {
  description = "WAF Web ACL Name"
  value       = var.create_waf ? module.waf[0].web_acl_name : null
}

output "waf_web_acl_capacity" {
  description = "WAF Web ACL Capacity"
  value       = var.create_waf ? module.waf[0].web_acl_capacity : null
}

# ===========================================
# Bastion Host Outputs
# ===========================================

output "bastion_instance_id" {
  description = "Bastion Host instance ID"
  value       = var.create_bastion ? module.bastion[0].bastion_instance_id : null
}

output "bastion_public_ip" {
  description = "Bastion Host public IP"
  value       = var.create_bastion ? module.bastion[0].bastion_public_ip : null
}

output "bastion_private_ip" {
  description = "Bastion Host private IP"
  value       = var.create_bastion ? module.bastion[0].bastion_private_ip : null
}

output "bastion_ssh_command" {
  description = "SSH command to connect to Bastion"
  value       = var.create_bastion ? module.bastion[0].ssh_command : null
}

output "bastion_security_group_id" {
  description = "Bastion Host security group ID"
  value       = module.security_groups.bastion_sg_id
}

# ===========================================
# K3s Cluster Outputs
# ===========================================

output "k3s_master_public_ip" {
  description = "K3s master public IP"
  value       = var.create_k3s ? module.k3s[0].master_public_ip : null
}

output "k3s_master_private_ip" {
  description = "K3s master private IP"
  value       = var.create_k3s ? module.k3s[0].master_private_ip : null
}

output "k3s_worker_instances" {
  description = "K3s worker instances"
  value       = var.create_k3s ? module.k3s[0].worker_instances : null
}

output "k3s_security_group_id" {
  description = "K3s security group ID"
  value       = var.create_k3s ? module.k3s[0].security_group_id : null
}

output "k3s_ssh_master_command" {
  description = "SSH command to K3s master"
  value       = var.create_k3s ? module.k3s[0].ssh_master_command : null
}

output "k3s_kubeconfig_command" {
  description = "Command to get kubeconfig from K3s master"
  value       = var.create_k3s ? module.k3s[0].kubeconfig_command : null
}
