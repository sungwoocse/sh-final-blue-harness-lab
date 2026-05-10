# ===========================================
# Bastion Host Outputs
# ===========================================

output "bastion_instance_id" {
  description = "Bastion Host instance ID"
  value       = aws_instance.bastion.id
}

output "bastion_public_ip" {
  description = "Bastion Host public IP"
  value       = var.allocate_eip ? aws_eip.bastion[0].public_ip : aws_instance.bastion.public_ip
}

output "bastion_private_ip" {
  description = "Bastion Host private IP"
  value       = aws_instance.bastion.private_ip
}

output "bastion_key_name" {
  description = "Bastion Host SSH key name"
  value       = var.key_name
}

output "ssh_command" {
  description = "SSH command to connect to Bastion"
  value       = "ssh -i ${var.key_name}.pem ec2-user@${var.allocate_eip ? aws_eip.bastion[0].public_ip : aws_instance.bastion.public_ip}"
}
