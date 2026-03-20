# orenoBiomni AWS Infrastructure
#
# Creates a self-contained VPC with public/private subnets, a GPU-capable EC2
# instance, and all supporting resources (security groups, IAM, EBS).
#
# Usage:
#   cd terraform/aws
#   terraform init
#   terraform plan -var="key_name=your-key" -var="allowed_cidr=YOUR_CIDR/24" -var="admin_cidr=YOUR_IP/32"
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

# ── Data sources ────────────────────────────────────────────────────────────

# Latest Ubuntu 22.04 Deep Learning AMI (has NVIDIA drivers pre-installed)
data "aws_ami" "ubuntu_dl" {
  most_recent = true
  owners      = ["898082745236"] # AWS Deep Learning AMIs

  filter {
    name   = "name"
    values = ["Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 22.04)*"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

# Availability zones in the selected region
data "aws_availability_zones" "available" {
  state = "available"
}

# ── VPC & Networking ────────────────────────────────────────────────────────

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name    = "${var.project_name}-vpc"
    Project = var.project_name
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name    = "${var.project_name}-igw"
    Project = var.project_name
  }
}

# Public subnet (for EC2 instance with internet access)
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name    = "${var.project_name}-public"
    Project = var.project_name
  }
}

# Private subnet (for future use: RDS, ElastiCache, etc.)
resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name    = "${var.project_name}-private"
    Project = var.project_name
  }
}

# Route table for public subnet
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name    = "${var.project_name}-public-rt"
    Project = var.project_name
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# ── Security Group ──────────────────────────────────────────────────────────

resource "aws_security_group" "biomni" {
  name        = "${var.project_name}-sg"
  description = "orenoBiomni - web access from allowed CIDR, SSH from admin CIDR"
  vpc_id      = aws_vpc.main.id

  # HTTP
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  # HTTPS
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
  }

  # SSH (admin only)
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]
  }

  # All outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "${var.project_name}-sg"
    Project = var.project_name
  }
}

# ── IAM Role ────────────────────────────────────────────────────────────────

# IAM role for EC2 instance (CloudWatch logs + S3 access)
resource "aws_iam_role" "ec2_role" {
  name = "${var.project_name}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project = var.project_name
  }
}

# CloudWatch Logs policy
resource "aws_iam_role_policy" "cloudwatch_logs" {
  name = "${var.project_name}-cloudwatch-logs"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:${var.region}:*:log-group:/${var.project_name}/*"
      }
    ]
  })
}

# S3 access policy (scoped to project bucket)
resource "aws_iam_role_policy" "s3_access" {
  name = "${var.project_name}-s3-access"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.project_name}-*",
          "arn:aws:s3:::${var.project_name}-*/*"
        ]
      }
    ]
  })
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

# ── EBS Data Volume ────────────────────────────────────────────────────────

resource "aws_ebs_volume" "data" {
  availability_zone = data.aws_availability_zones.available.names[0]
  size              = var.volume_size
  type              = "gp3"
  throughput        = 500
  iops              = 6000
  encrypted         = true

  tags = {
    Name    = "${var.project_name}-data"
    Project = var.project_name
  }
}

# ── EC2 Instance ────────────────────────────────────────────────────────────

resource "aws_instance" "biomni" {
  ami                    = var.ami_id != "" ? var.ami_id : data.aws_ami.ubuntu_dl.id
  instance_type          = var.instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.biomni.id]
  subnet_id              = aws_subnet.public.id
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  root_block_device {
    volume_size = 100
    volume_type = "gp3"
    encrypted   = true
  }

  # User data: runs deploy.sh on first boot
  user_data = <<-USERDATA
    #!/bin/bash
    set -e
    exec > /var/log/orenoiomni-init.log 2>&1

    echo "=== orenoBiomni instance initialization ==="
    date

    # Wait for EBS volume to attach
    echo "Waiting for data volume..."
    while [ ! -e /dev/nvme1n1 ] && [ ! -e /dev/xvdf ]; do
      sleep 2
    done

    # Determine the data device name (NVMe vs traditional)
    if [ -e /dev/nvme1n1 ]; then
      DATA_DEV=/dev/nvme1n1
    else
      DATA_DEV=/dev/xvdf
    fi

    # Format if unformatted, then mount
    mkdir -p /data
    if ! blkid "$DATA_DEV" 2>/dev/null; then
      echo "Formatting $DATA_DEV..."
      mkfs.ext4 "$DATA_DEV"
    fi
    mount "$DATA_DEV" /data
    echo "$DATA_DEV /data ext4 defaults,nofail 0 2" >> /etc/fstab

    # Create data subdirectories
    mkdir -p /data/ollama /data/biomni /data/postgres /data/redis
    chown -R 1000:1000 /data

    # Install Docker
    if ! command -v docker &>/dev/null; then
      curl -fsSL https://get.docker.com | sh
      usermod -aG docker ubuntu
    fi

    # Install NVIDIA Container Toolkit (Deep Learning AMI has drivers)
    if ! command -v nvidia-ctk &>/dev/null; then
      curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
        gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
      curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
      apt-get update && apt-get install -y nvidia-container-toolkit
      nvidia-ctk runtime configure --runtime=docker
      systemctl restart docker
    fi

    # Clone and deploy as ubuntu user
    su - ubuntu -c '
      set -e
      cd /home/ubuntu

      # Clone project
      if [ ! -d orenoBiomni ]; then
        git clone https://github.com/inutano/orenoBiomni.git
      fi
      cd orenoBiomni

      # Clone Biomni
      if [ ! -d Biomni ]; then
        git clone https://github.com/snap-stanford/Biomni.git
      fi

      # Run deploy script
      bash scripts/deploy.sh --gpu --skip-drivers
    '

    echo "=== orenoBiomni initialization complete ==="
    date
  USERDATA

  tags = {
    Name    = "${var.project_name}-gpu"
    Project = var.project_name
  }

  # Prevent accidental termination
  disable_api_termination = false

  lifecycle {
    # Don't replace instance when user_data changes
    ignore_changes = [user_data]
  }
}

# Attach data volume to instance
resource "aws_volume_attachment" "data" {
  device_name = "/dev/xvdf"
  volume_id   = aws_ebs_volume.data.id
  instance_id = aws_instance.biomni.id
}
