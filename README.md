# Terracore Ventures: Real Estate Investment Platform

This repository contains the full-stack code and infrastructure for the Terracore Ventures real estate investment analysis and management platform.

## Structure

- `app/` — Flask web application, Docker, Gunicorn, requirements, etc.
- `infra/` — Terraform code for AWS (EC2, VPC, Route53, budgets, etc.), EC2 bootstrap scripts, and related infrastructure.
- `docs/` — Business plan and supporting documentation.

## Deployment Workflow

1. **Local Development**: Develop and test the Flask app locally using Docker.
2. **Infrastructure Provisioning**: Use Terraform in `infra/` to provision AWS resources (EC2, VPC, security groups, Route53 DNS, budgets, etc.).
3. **EC2 Bootstrap**: On first boot, the EC2 instance runs a script to install MySQL, Docker, docker-compose, and configures the app/database.
4. **Production Deployment**: The Flask app runs in Docker with Gunicorn, connects to the local MySQL instance, and is served over HTTPS using Let's Encrypt certificates.

See `infra/README.md` and `app/README.md` for details on each component.