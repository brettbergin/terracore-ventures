variable "aws_region" {
  description = "AWS region to deploy resources in."
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type."
  type        = string
  default     = "t3.small"
}

variable "ami_id" {
  description = "AMI ID for Ubuntu 22.04."
  type        = string
}

variable "key_name" {
  description = "EC2 key pair name for SSH access."
  type        = string
}

variable "route53_zone_id" {
  description = "Route53 Hosted Zone ID for terracoreventures.com."
  type        = string
}

variable "budget_amount" {
  description = "Monthly AWS budget in USD."
  type        = string
  default     = "50"
}

variable "budget_email" {
  description = "Email address for AWS budget alerts."
  type        = string
} 