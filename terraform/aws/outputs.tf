# orenoBiomni Terraform Outputs

output "public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.biomni.public_ip
}

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.biomni.id
}

output "private_ip" {
  description = "Private IP address (for VPC-internal access)"
  value       = aws_instance.biomni.private_ip
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i ~/.ssh/${var.key_name}.pem ubuntu@${aws_instance.biomni.public_ip}"
}

output "app_url" {
  description = "Application URL (HTTPS)"
  value       = "https://${aws_instance.biomni.public_ip}"
}

output "api_docs_url" {
  description = "API documentation URL"
  value       = "https://${aws_instance.biomni.public_ip}/docs"
}

output "init_log_command" {
  description = "Command to check initialization progress"
  value       = "ssh -i ~/.ssh/${var.key_name}.pem ubuntu@${aws_instance.biomni.public_ip} 'sudo tail -f /var/log/orenoiomni-init.log'"
}
