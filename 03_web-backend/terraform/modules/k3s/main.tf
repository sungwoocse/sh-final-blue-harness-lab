# ===========================================
# K3s Cluster Module - EC2 Instances
# ===========================================

# 최신 Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# ===========================================
# K3s Master (Control Plane)
# ===========================================

resource "aws_instance" "k3s_master" {
  ami                         = var.ami_id != "" ? var.ami_id : data.aws_ami.amazon_linux_2023.id
  instance_type               = var.master_instance_type
  key_name                    = var.key_name
  subnet_id                   = var.subnet_ids[0]
  vpc_security_group_ids      = [aws_security_group.k3s.id]
  iam_instance_profile        = aws_iam_instance_profile.k3s_control_plane.name
  associate_public_ip_address = true

  root_block_device {
    volume_size           = var.master_volume_size
    volume_type           = "gp3"
    delete_on_termination = true
    encrypted             = true
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" # IMDSv2 강제 (보안 권장)
    http_put_response_hop_limit = 2          # 컨테이너 워크로드용 (기본값 1 -> 2)
  }


  tags = merge(var.tags, {
    Name = "${var.name_prefix}-k3s-master"
    Role = "k3s-master"
  })

}

# ===========================================
# K3s Workers
# ===========================================

resource "aws_instance" "k3s_workers" {
  for_each = var.workers

  ami                         = var.ami_id != "" ? var.ami_id : data.aws_ami.amazon_linux_2023.id
  instance_type               = each.value.instance_type
  key_name                    = var.key_name
  subnet_id                   = var.subnet_ids[each.value.subnet_index % length(var.subnet_ids)]
  vpc_security_group_ids      = [aws_security_group.k3s.id]
  iam_instance_profile        = aws_iam_instance_profile.k3s_worker.name
  associate_public_ip_address = true

  root_block_device {
    volume_size           = each.value.volume_size
    volume_type           = "gp3"
    delete_on_termination = true
    encrypted             = true
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" # IMDSv2 강제 (보안 권장)
    http_put_response_hop_limit = 2          # 컨테이너 워크로드용 (기본값 1 -> 2)
  }


  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-${each.key}"
    Role     = "k3s-worker"
    Workload = each.value.workload
  })

  depends_on = [aws_instance.k3s_master]
}

# ===========================================
# Elastic IPs
# ===========================================

resource "aws_eip" "k3s_master" {
  count    = var.allocate_eip ? 1 : 0
  instance = aws_instance.k3s_master.id
  domain   = "vpc"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-k3s-master-eip"
  })
}
