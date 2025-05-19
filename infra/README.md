# Infrastructure: AWS & Deployment

This directory contains all infrastructure-as-code and automation for deploying the Terracore Ventures web application to AWS.

## Components
- **Terraform**: Provisions VPC, subnet, security group, EC2 instance, EIP, Route53 DNS, AWS Budgets, and CloudWatch monitoring.
- **Bootstrap Script**: Installs MySQL, Docker, docker-compose, and configures the Flask app and database on the EC2 instance.

## Setup Instructions

1. **AWS Credentials**: Configure your AWS credentials (via `aws configure` or environment variables).
2. **Terraform Init**:
   ```sh
   cd infra
   terraform init
   ```
3. **Terraform Plan**:
   ```sh
   terraform plan
   ```
4. **Terraform Apply**:
   ```sh
   terraform apply
   ```
   This will provision all required AWS resources and output the public DNS/IP for your EC2 instance.

5. **DNS Setup**: Route53 records will be created for `www.terracoreventures.com`.

6. **First Boot**: The EC2 instance will run the bootstrap script to install MySQL, Docker, and the Flask app.

See `main.tf` and `scripts/ec2_bootstrap.sh` for details. 