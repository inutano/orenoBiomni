# orenoBiomni AWS Infrastructure
#
# Usage:
#   cd terraform/aws
#   terraform init
#   terraform plan -var="ssh_key_name=your-key" -var="allowed_cidr=YOUR_UNIV_CIDR/24"
#   terraform apply

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# Security group: restrict to university network
resource "aws_security_group" "biomni" {
  name        = "orenoiomni-sg"
  description = "orenoBiomni - university access only"
  vpc_id      = var.vpc_id

  # Biomni UI
  ingress {
    description = "Biomni Gradio UI"
    from_port   = 7860
    to_port     = 7860
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  # SSH
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  # All outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "orenoiomni"
    Project = "orenoBiomni"
  }
}

# EBS volume for persistent data (Ollama models + Biomni data lake)
resource "aws_ebs_volume" "data" {
  availability_zone = "${var.region}${var.az_suffix}"
  size              = var.data_volume_size
  type              = "gp3"
  throughput        = 500
  iops              = 6000

  tags = {
    Name    = "orenoiomni-data"
    Project = "orenoBiomni"
  }
}

# GPU instance
resource "aws_instance" "biomni" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = var.ssh_key_name
  vpc_security_group_ids = [aws_security_group.biomni.id]
  subnet_id              = var.subnet_id
  availability_zone      = "${var.region}${var.az_suffix}"

  root_block_device {
    volume_size = 100
    volume_type = "gp3"
  }

  user_data = <<-EOF
    #!/bin/bash
    set -e

    # Install Docker
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker ubuntu

    # Install NVIDIA Container Toolkit
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
      gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
      sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
      tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
    apt-get update && apt-get install -y nvidia-container-toolkit
    nvidia-ctk runtime configure --runtime=docker
    systemctl restart docker

    # Mount data volume
    mkdir -p /data
    # Note: volume attachment handled separately; format if needed
    if ! blkid /dev/nvme1n1; then
      mkfs.ext4 /dev/nvme1n1
    fi
    mount /dev/nvme1n1 /data
    echo '/dev/nvme1n1 /data ext4 defaults,nofail 0 2' >> /etc/fstab

    # Clone project
    su - ubuntu -c "
      git clone https://github.com/inutano/orenoBiomni.git /home/ubuntu/orenoBiomni
      cd /home/ubuntu/orenoBiomni
      git clone https://github.com/snap-stanford/Biomni.git
      ln -sf /data/ollama /home/ubuntu/orenoBiomni/ollama-data
      ln -sf /data/biomni /home/ubuntu/orenoBiomni/Biomni/data
    "
  EOF

  tags = {
    Name    = "orenoiomni-gpu"
    Project = "orenoBiomni"
  }
}

# Attach data volume
resource "aws_volume_attachment" "data" {
  device_name = "/dev/xvdf"
  volume_id   = aws_ebs_volume.data.id
  instance_id = aws_instance.biomni.id
}
