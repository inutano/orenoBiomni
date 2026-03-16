output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.biomni.id
}

output "public_ip" {
  description = "Public IP address"
  value       = aws_instance.biomni.public_ip
}

output "private_ip" {
  description = "Private IP address"
  value       = aws_instance.biomni.private_ip
}

output "biomni_url" {
  description = "Biomni UI URL"
  value       = "http://${aws_instance.biomni.public_ip}:7860"
}

output "ssh_command" {
  description = "SSH command to connect"
  value       = "ssh -i ~/.ssh/${var.ssh_key_name}.pem ubuntu@${aws_instance.biomni.public_ip}"
}
