# Flask Application

This directory contains the Flask web application for Terracore Ventures, including Docker configuration and Gunicorn setup.

## Features
- Google SSO authentication (admin/standard roles)
- SQLAlchemy ORM, Flask-Migrate for migrations
- Bootstrap UI with Jinja2 templates
- ChatGPT API integration for property analysis

## Local Development

1. **Install Docker** (if not already installed)
2. **Clone the repo and enter the app directory**
3. **Copy `.env.example` to `.env` and fill in secrets (Google OAuth, DB, ChatGPT API key)**
4. **Run the app:**
   ```sh
   docker-compose up --build
   ```
   The app will be available at http://localhost:5000

## Production
- In production, the app runs behind Gunicorn in Docker, connecting to MySQL on the EC2 host.
- HTTPS is handled by the EC2 host using Let's Encrypt.

See `Dockerfile`, `docker-compose.yml`, and `terracore/` for details. 