# ===========================================
# K3s Module Outputs
# ===========================================

output "master_instance_id" {
  description = "K3s master instance ID"
  value       = aws_instance.k3s_master.id
}

output "master_public_ip" {
  description = "K3s master public IP"
  value       = var.allocate_eip ? aws_eip.k3s_master[0].public_ip : aws_instance.k3s_master.public_ip
}

output "master_private_ip" {
  description = "K3s master private IP"
  value       = aws_instance.k3s_master.private_ip
}

output "worker_instances" {
  description = "K3s worker instances"
  value = {
    for k, v in aws_instance.k3s_workers : k => {
      id         = v.id
      public_ip  = v.public_ip
      private_ip = v.private_ip
    }
  }
}

output "security_group_id" {
  description = "K3s security group ID"
  value       = aws_security_group.k3s.id
}

output "kubeconfig_command" {
  description = "Command to get kubeconfig"
  value       = "ssh -i ${var.key_name}.pem ec2-user@${var.allocate_eip ? aws_eip.k3s_master[0].public_ip : aws_instance.k3s_master.public_ip} 'sudo cat /etc/rancher/k3s/k3s.yaml'"
}

output "ssh_master_command" {
  description = "SSH command to master"
  value       = "ssh -i ${var.key_name}.pem ec2-user@${var.allocate_eip ? aws_eip.k3s_master[0].public_ip : aws_instance.k3s_master.public_ip}"
}
