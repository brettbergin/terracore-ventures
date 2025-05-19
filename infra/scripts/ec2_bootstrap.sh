#!/bin/bash
set -e

# Variables (replace these with actual values or use Terraform templatefile for secrets)
MYSQL_ROOT_PASSWORD="changeme_root"
MYSQL_APP_DB="terracore"
MYSQL_APP_USER="appuser"
MYSQL_APP_PASS="apppassword"

# Update and install dependencies
apt-get update
apt-get upgrade -y
apt-get install -y mysql-server docker.io docker-compose nginx python3-certbot-nginx awscli python3-pip
pip3 install boto3

# Configure MySQL to listen only on 127.0.0.1
sed -i "s/^bind-address.*/bind-address = 127.0.0.1/" /etc/mysql/mysql.conf.d/mysqld.cnf
systemctl restart mysql

# Secure MySQL and create app DB/user
mysql -u root <<EOF
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '$MYSQL_ROOT_PASSWORD';
CREATE DATABASE IF NOT EXISTS $MYSQL_APP_DB;
CREATE USER IF NOT EXISTS '$MYSQL_APP_USER'@'localhost' IDENTIFIED BY '$MYSQL_APP_PASS';
GRANT ALL PRIVILEGES ON $MYSQL_APP_DB.* TO '$MYSQL_APP_USER'@'localhost';
FLUSH PRIVILEGES;
EOF

# Enable and start MySQL and Docker
systemctl enable mysql	systemctl start mysql
systemctl enable docker	 systemctl start docker

# (Optional) Add ubuntu user to docker group
usermod -aG docker ubuntu || true

# Print status
systemctl status mysql --no-pager
systemctl status docker --no-pager

# Configure Nginx as reverse proxy for Flask (Gunicorn)
cat >/etc/nginx/sites-available/terracore <<EOF
server {
    listen 80;
    server_name www.terracoreventures.com;
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
ln -sf /etc/nginx/sites-available/terracore /etc/nginx/sites-enabled/terracore
rm -f /etc/nginx/sites-enabled/default
systemctl restart nginx

# Obtain Let's Encrypt cert (Route53 DNS validation)
# (Assumes AWS CLI is configured and Route53 zone exists)
certbot --nginx --non-interactive --agree-tos --email admin@terracoreventures.com -d www.terracoreventures.com --redirect

systemctl reload nginx

echo "MySQL and Docker installed and configured. Nginx and HTTPS configured with Let's Encrypt."

# --- Deploy Flask App with Docker Compose ---
APP_DIR="/opt/terracore-ventures"
REPO_URL="https://github.com/brettbergin/terracore-ventures.git"

if [ ! -d "$APP_DIR" ]; then
  git clone $REPO_URL $APP_DIR
else
  cd $APP_DIR && git pull
fi

# --- Python Virtualenv Setup ---
cd $APP_DIR
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r app/requirements.txt
cd app
# Ensure .env is not used; Flask will fetch secrets from AWS Secrets Manager
docker-compose up -d

echo "Flask app deployed and running in Docker." 