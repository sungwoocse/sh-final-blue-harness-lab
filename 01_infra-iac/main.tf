# ===========================================
# VPC Module
# ===========================================

module "vpc" {
  source = "./modules/vpc"

  name              = var.project_name
  vpc_cidr          = var.vpc_cidr
  azs               = var.availability_zones
  public_cidrs      = var.public_subnet_cidrs
  private_app_cidrs = var.private_app_subnet_cidrs
  private_db_cidrs  = var.private_db_subnet_cidrs
}

# ===========================================
# Security Groups Module
# ===========================================

module "security_groups" {
  source = "./modules/security-groups"

  name_prefix                 = var.project_name
  vpc_id                      = module.vpc.vpc_id
  create_rds_sg               = false
  create_bastion_sg           = var.create_bastion
  bastion_allowed_cidr_blocks = var.bastion_allowed_cidr_blocks

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ===========================================
# ECR Repositories Module
# ===========================================

module "ecr" {
  source = "./modules/ecr"

  project_name = var.project_name

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ===========================================
# Application Load Balancer Module
# ===========================================

module "alb" {
  source = "./modules/alb"

  name_prefix           = var.project_name
  vpc_id                = module.vpc.vpc_id
  public_subnet_ids     = module.vpc.public_subnet
  alb_security_group_id = module.security_groups.alb_sg_id
  certificate_arn       = var.alb_certificate_arn

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ===========================================
# WAF for CloudFront Module
# ===========================================

module "waf" {
  source = "./modules/waf"
  count  = var.create_waf ? 1 : 0

  providers = {
    aws = aws.us_east_1
  }

  name_prefix               = var.project_name
  rate_limit                = var.waf_rate_limit
  enable_cloudwatch_metrics = var.waf_enable_cloudwatch_metrics
  enable_sampled_requests   = var.waf_enable_sampled_requests

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ===========================================
# CloudFront Distribution Module (S3 Frontend - www.eunha.icu)
# ===========================================

module "cloudfront" {
  source = "./modules/cloudfront"
  count  = var.create_cloudfront ? 1 : 0

  name_prefix          = var.project_name
  s3_bucket_name       = var.frontend_s3_bucket_name
  acm_certificate_arn  = var.cloudfront_certificate_arn
  aliases              = ["www.eunha.icu"]
  price_class          = "PriceClass_100"
  web_acl_id           = var.create_waf ? module.waf[0].web_acl_arn : ""
  cors_allowed_origins = ["https://www.eunha.icu"]

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ===========================================
# Bastion Host Module
# ===========================================

module "bastion" {
  source = "./modules/bastion"
  count  = var.create_bastion ? 1 : 0

  name_prefix       = var.project_name
  public_subnet_id  = module.vpc.public_subnet[0]
  security_group_id = module.security_groups.bastion_sg_id
  instance_type     = var.bastion_instance_type
  allocate_eip      = var.bastion_allocate_eip
  root_volume_size  = var.bastion_root_volume_size
  ami_id            = var.bastion_ami_id
  key_name          = var.bastion_key_name

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ===========================================
# K3s Cluster Module
# ===========================================

module "k3s" {
  source = "./modules/k3s"
  count  = var.create_k3s ? 1 : 0

  name_prefix          = var.project_name
  vpc_id               = module.vpc.vpc_id
  subnet_ids           = module.vpc.public_subnet
  key_name             = var.k3s_key_name
  master_instance_type = var.k3s_master_instance_type
  master_volume_size   = var.k3s_master_volume_size
  k3s_token            = var.k3s_token
  allocate_eip         = var.k3s_allocate_eip

  workers = {
    "worker-wasm" = {
      instance_type = var.k3s_worker_instance_type
      volume_size   = var.k3s_worker_volume_size
      role          = "worker"
      workload      = "wasm"
      subnet_index  = 0
    }
    "worker-build" = {
      instance_type = var.k3s_worker_instance_type
      volume_size   = var.k3s_worker_volume_size
      role          = "worker"
      workload      = "build"
      subnet_index  = 1
    }
    "worker-observability" = {
      instance_type = var.k3s_worker_instance_type
      volume_size   = var.k3s_worker_volume_size
      role          = "worker"
      workload      = "observability"
      subnet_index  = 0
    }
    "worker-infra" = {
      instance_type = var.k3s_worker_instance_type
      volume_size   = var.k3s_worker_volume_size
      role          = "worker"
      workload      = "infra"
      subnet_index  = 1
    }
  }

  allowed_ssh_cidr_blocks = var.k3s_allowed_ssh_cidr_blocks

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}
