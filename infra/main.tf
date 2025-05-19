// Terraform main configuration for Terracore Ventures AWS infrastructure

provider "aws" {
  region = var.aws_region
}

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  enable_dns_support = true
  enable_dns_hostnames = true
  tags = { Name = "terracore-vpc" }
}

resource "aws_subnet" "main" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = data.aws_availability_zones.available.names[0]
  tags = { Name = "terracore-subnet" }
}

data "aws_availability_zones" "available" {}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route_table" "rt" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }
}

resource "aws_route_table_association" "a" {
  subnet_id      = aws_subnet.main.id
  route_table_id = aws_route_table.rt.id
}

resource "aws_security_group" "web" {
  name        = "terracore-web-sg"
  description = "Allow HTTPS and SSH"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "web" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.main.id
  vpc_security_group_ids = [aws_security_group.web.id]
  associate_public_ip_address = true
  key_name               = var.key_name
  user_data              = file("${path.module}/scripts/ec2_bootstrap.sh")
  tags = { Name = "terracore-web" }
}

resource "aws_eip" "web" {
  instance = aws_instance.web.id
  vpc      = true
}

resource "aws_route53_record" "www" {
  zone_id = var.route53_zone_id
  name    = "www"
  type    = "A"
  ttl     = 300
  records = [aws_eip.web.public_ip]
}

resource "aws_budgets_budget" "monthly" {
  name              = "terracore-monthly-budget"
  budget_type       = "COST"
  limit_amount      = var.budget_amount
  limit_unit        = "USD"
  time_unit         = "MONTHLY"
  cost_types {
    include_tax = true
  }
  notification {
    comparison_operator = "GREATER_THAN"
    notification_type   = "ACTUAL"
    threshold           = 80
    threshold_type      = "PERCENTAGE"
    subscriber_email_addresses = [var.budget_email]
  }
}

resource "aws_cloudwatch_log_group" "web" {
  name = "/terracore/web"
  retention_in_days = 30
}

resource "aws_secretsmanager_secret" "flask_secret_key" {
  name = "terracore/FLASK_SECRET_KEY"
}
resource "aws_secretsmanager_secret" "mysql_user" {
  name = "terracore/MYSQL_USER"
}
resource "aws_secretsmanager_secret" "mysql_password" {
  name = "terracore/MYSQL_PASSWORD"
}
resource "aws_secretsmanager_secret" "google_oauth_client_id" {
  name = "terracore/GOOGLE_OAUTH_CLIENT_ID"
}
resource "aws_secretsmanager_secret" "google_oauth_client_secret" {
  name = "terracore/GOOGLE_OAUTH_CLIENT_SECRET"
}
resource "aws_secretsmanager_secret" "openai_api_key" {
  name = "terracore/OPENAI_API_KEY"
} 