output "ec2_public_ip" {
  description = "Public IP address of the EC2 instance."
  value       = aws_eip.web.public_ip
}

output "ec2_dns_name" {
  description = "Public DNS name of the EC2 instance."
  value       = aws_instance.web.public_dns
}

output "route53_www_record" {
  description = "Route53 www record for the application."
  value       = aws_route53_record.www.fqdn
}

output "flask_secret_key_arn" {
  value = aws_secretsmanager_secret.flask_secret_key.arn
}

output "mysql_user_arn" {
  value = aws_secretsmanager_secret.mysql_user.arn
}

output "mysql_password_arn" {
  value = aws_secretsmanager_secret.mysql_password.arn
}

output "google_oauth_client_id_arn" {
  value = aws_secretsmanager_secret.google_oauth_client_id.arn
}

output "google_oauth_client_secret_arn" {
  value = aws_secretsmanager_secret.google_oauth_client_secret.arn
}

output "openai_api_key_arn" {
  value = aws_secretsmanager_secret.openai_api_key.arn
} 