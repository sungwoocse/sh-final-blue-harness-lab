locals {
  public_az = { for i, az in var.azs : az => { cidr = var.public_cidrs[i] } }
  app_az    = { for i, az in var.azs : az => { cidr = var.private_app_cidrs[i] } }
  db_az     = { for i, az in var.azs : az => { cidr = var.private_db_cidrs[i] } }
  nat_az    = var.azs[0]
}

# --- VPC & IGW ---
resource "aws_vpc" "vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "${var.name}-vpc" }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.vpc.id
  tags   = { Name = "${var.name}-igw" }
}

# --- Subnets ---

resource "aws_subnet" "public" {
  for_each                = local.public_az
  vpc_id                  = aws_vpc.vpc.id
  cidr_block              = each.value.cidr
  availability_zone       = each.key
  map_public_ip_on_launch = true
  tags = {
    Tier                                   = "public",
    Name                                   = "${var.name}-public-subnet-${each.key}",
    "kubernetes.io/role/elb"               = "1",
    "kubernetes.io/cluster/ticket-cluster" = "owned"
  }
}

resource "aws_subnet" "private_app" {
  for_each                = local.app_az
  vpc_id                  = aws_vpc.vpc.id
  cidr_block              = each.value.cidr
  availability_zone       = each.key
  map_public_ip_on_launch = false
  tags = {
    Tier                                   = "private-app",
    Name                                   = "${var.name}-app-subnet-${each.key}",
    "kubernetes.io/role/internal-elb"      = "1",
    "kubernetes.io/cluster/ticket-cluster" = "owned",
    "karpenter.sh/discovery"               = "ticket-cluster"
  }
}

resource "aws_subnet" "private_db" {
  for_each                = local.db_az
  vpc_id                  = aws_vpc.vpc.id
  cidr_block              = each.value.cidr
  availability_zone       = each.key
  map_public_ip_on_launch = false
  tags = {
    Tier                              = "private-db",
    Name                              = "${var.name}-db-subnet-${each.key}",
    "kubernetes.io/role/internal-elb" = "1"
  }
}

resource "aws_eip" "nat" {
  domain = "vpc"
  count  = 1
  tags   = { Name = "${var.name}-eip" }
}

resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[local.nat_az].id
  tags          = { Name = "${var.name}-nat" }
  depends_on    = [aws_internet_gateway.igw, aws_eip.nat]
}

# --- Route Tables (Public)---
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.vpc.id
  tags   = { Name = "${var.name}-rt-public" }
}

resource "aws_route" "public" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.igw.id
}

resource "aws_route_table_association" "public" {
  for_each       = aws_subnet.public
  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

# --- Route Tables (Private-app)---
resource "aws_route_table" "app" {
  vpc_id = aws_vpc.vpc.id
  tags   = { Name = "${var.name}-rt-private-app" }
}

resource "aws_route" "app" {
  route_table_id         = aws_route_table.app.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.nat.id
  depends_on             = [aws_nat_gateway.nat]
}

resource "aws_route_table_association" "app" {
  for_each       = aws_subnet.private_app
  subnet_id      = each.value.id
  route_table_id = aws_route_table.app.id
}

# --- Route Tables (Private-db)---
resource "aws_route_table" "db" {
  vpc_id = aws_vpc.vpc.id
  tags   = { Name = "${var.name}-rt-private-db" }
}

resource "aws_route_table_association" "db" {
  for_each       = aws_subnet.private_db
  subnet_id      = each.value.id
  route_table_id = aws_route_table.db.id
}

# --- S3 Gateway Endpoint (무료) ---
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.vpc.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"

  route_table_ids = [
    aws_route_table.app.id,
    aws_route_table.db.id
  ]

  tags = { Name = "${var.name}-s3-endpoint" }
}
