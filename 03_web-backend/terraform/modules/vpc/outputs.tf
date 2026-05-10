output "vpc_id" {
  description = "The ID of the VPC"
  value       = aws_vpc.vpc.id
}

output "public_subnet" {
  description = "List of IDs of public subnets"
  value       = [for s in aws_subnet.public : s.id]
}

output "app_subnet" {
  description = "List of IDs of private application subnets"
  value       = [for s in aws_subnet.private_app : s.id]
}

output "db_subnet" {
  description = "List of IDs of private database subnets"
  value       = [for s in aws_subnet.private_db : s.id]
}

output "vpc_cidr" {
  description = "The CIDR block of the VPC"
  value       = aws_vpc.vpc.cidr_block
}
