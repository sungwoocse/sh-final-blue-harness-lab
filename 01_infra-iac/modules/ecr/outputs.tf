# ECR Repository URLs
output "backend_repository_url" {
  description = "URL of the Backend ECR repository"
  value       = aws_ecr_repository.backend.repository_url
}

output "frontend_repository_url" {
  description = "URL of the Frontend ECR repository"
  value       = aws_ecr_repository.frontend.repository_url
}

output "faas_builder_repository_url" {
  description = "URL of the FaaS Builder ECR repository"
  value       = aws_ecr_repository.faas_builder.repository_url
}

output "faas_app_repository_url" {
  description = "URL of the FaaS App ECR repository"
  value       = aws_ecr_repository.faas_app.repository_url
}

# ECR Repository Names
output "backend_repository_name" {
  description = "Name of the Backend ECR repository"
  value       = aws_ecr_repository.backend.name
}

output "frontend_repository_name" {
  description = "Name of the Frontend ECR repository"
  value       = aws_ecr_repository.frontend.name
}

output "faas_builder_repository_name" {
  description = "Name of the FaaS Builder ECR repository"
  value       = aws_ecr_repository.faas_builder.name
}

output "faas_app_repository_name" {
  description = "Name of the FaaS App ECR repository"
  value       = aws_ecr_repository.faas_app.name
}

# ECR Repository ARNs
output "backend_repository_arn" {
  description = "ARN of the Backend ECR repository"
  value       = aws_ecr_repository.backend.arn
}

output "frontend_repository_arn" {
  description = "ARN of the Frontend ECR repository"
  value       = aws_ecr_repository.frontend.arn
}

output "faas_builder_repository_arn" {
  description = "ARN of the FaaS Builder ECR repository"
  value       = aws_ecr_repository.faas_builder.arn
}

output "faas_app_repository_arn" {
  description = "ARN of the FaaS App ECR repository"
  value       = aws_ecr_repository.faas_app.arn
}

# All repositories as a map for convenience
output "ecr_repositories" {
  description = "Map of all ECR repositories with their URLs and names"
  value = {
    backend = {
      name = aws_ecr_repository.backend.name
      url  = aws_ecr_repository.backend.repository_url
      arn  = aws_ecr_repository.backend.arn
    }
    frontend = {
      name = aws_ecr_repository.frontend.name
      url  = aws_ecr_repository.frontend.repository_url
      arn  = aws_ecr_repository.frontend.arn
    }
    faas_builder = {
      name = aws_ecr_repository.faas_builder.name
      url  = aws_ecr_repository.faas_builder.repository_url
      arn  = aws_ecr_repository.faas_builder.arn
    }
    faas_app = {
      name = aws_ecr_repository.faas_app.name
      url  = aws_ecr_repository.faas_app.repository_url
      arn  = aws_ecr_repository.faas_app.arn
    }
  }
}
