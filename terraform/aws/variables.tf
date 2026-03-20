# orenoBiomni Terraform Variables
#
# Required: key_name, allowed_cidr, admin_cidr
# Optional: everything else has sensible defaults

variable "region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-west-2"
}

variable "instance_type" {
  description = "EC2 instance type. Use g5.xlarge (1x A10G 24GB) or g5.2xlarge for more CPU/RAM"
  type        = string
  default     = "g5.xlarge"
}

variable "ami_id" {
  description = "AMI ID. Leave empty to auto-select latest Ubuntu 22.04 Deep Learning AMI"
  type        = string
  default     = ""
}

variable "key_name" {
  description = "Name of the SSH key pair for EC2 access"
  type        = string
}

variable "allowed_cidr" {
  description = "CIDR block allowed to access HTTP/HTTPS (e.g., university IP range). Restrict this in production"
  type        = string
  default     = "0.0.0.0/0"
}

variable "admin_cidr" {
  description = "CIDR block allowed SSH access (e.g., your IP/32)"
  type        = string
}

variable "volume_size" {
  description = "Size of the persistent EBS data volume in GB"
  type        = number
  default     = 100
}

variable "app_domain" {
  description = "Optional domain name for the application (for SSL certificates)"
  type        = string
  default     = ""
}

variable "project_name" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "orenoiomni"
}
