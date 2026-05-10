# ===========================================
# Database Credentials Secret
# ===========================================

resource "aws_secretsmanager_secret" "database" {
  name        = "${var.name_prefix}/database/credentials"
  description = "Database credentials for ${var.name_prefix}"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-database-credentials"
  })
}

resource "aws_secretsmanager_secret_version" "database" {
  secret_id = aws_secretsmanager_secret.database.id
  secret_string = jsonencode({
    host     = var.db_host
    port     = var.db_port
    username = var.db_username
    password = var.db_password
    database = var.db_name
  })
}
