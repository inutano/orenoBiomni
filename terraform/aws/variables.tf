variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "az_suffix" {
  description = "Availability zone suffix"
  type        = string
  default     = "a"
}

variable "vpc_id" {
  description = "VPC ID to deploy into"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID to deploy into"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type (GPU required)"
  type        = string
  default     = "g5.2xlarge" # 1x A10G 24GB, 8 vCPU, 32GB RAM
}

variable "ami_id" {
  description = "AMI ID (Ubuntu 22.04 with NVIDIA drivers)"
  type        = string
  default     = "ami-0735c191cf914754d" # Ubuntu 22.04 LTS us-west-2 (update as needed)
}

variable "ssh_key_name" {
  description = "SSH key pair name for EC2 access"
  type        = string
}

variable "allowed_cidr" {
  description = "CIDR block allowed to access (e.g., university network)"
  type        = string
}

variable "data_volume_size" {
  description = "Size of persistent data EBS volume in GB"
  type        = number
  default     = 200 # Ollama models (~40GB) + data lake (~11GB) + headroom
}
