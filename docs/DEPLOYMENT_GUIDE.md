# FixMate — Production Deployment & Operations Guide

## 1. Overview
FixMate is production-ready for deployment on modern cloud platforms (Render, Railway, AWS EC2, or DigitalOcean Ubuntu Droplet) utilizing **Gunicorn WSGI**, **Nginx reverse proxy**, and a managed **MySQL** service.

---

## 2. Environment Variables Specification

Create an environment file (`.env`) on the host server:

| Variable Name | Required | Example Production Value | Purpose |
|---|---|---|---|
| `FLASK_ENV` | Yes | `production` | Enables production security settings |
| `SECRET_KEY` | Yes | `c839f2a0918b438290f12a3b4c5d6e7f` | Signs session cookies and CSRF tokens |
| `DATABASE_URL` | Yes | `mysql+pymysql://user:pass@db-host:3306/fixmate_db?charset=utf8mb4` | Production MySQL connection string |
| `UPLOAD_FOLDER` | Yes | `/var/fixmate/uploads` | Persistent storage for provider KYC documents |
| `COMMISSION_PERCENTAGE` | No | `10.0` | Default platform commission percentage |
| `CANCELLATION_FEE_PERCENTAGE` | No | `10.0` | Cancellation fee percentage |
| `CANCELLATION_WINDOW_MINUTES` | No | `15` | Window before cancellation fee applies |
| `GST_PERCENTAGE` | No | `18.0` | Tax rate applied to services |
| `DEMO_MODE` | No | `False` | Disables demo credentials and banners |

---

## 3. Ubuntu Linux Production Setup (Gunicorn + Nginx + Systemd)

### Step 1: System Packages & Python Virtual Environment
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12 python3.12-venv mysql-server nginx git

git clone https://github.com/your-username/fixmate.git /var/www/fixmate
cd /var/www/fixmate
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 2: Database Initialization & Migrations
```bash
# Apply production database schema
flask db upgrade

# Create Super Administrator account via CLI
flask create-admin
```

### Step 3: Systemd Service Configuration (`/etc/systemd/system/fixmate.service`)
```ini
[Unit]
Description=FixMate Gunicorn Application Server
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/fixmate
Environment="PATH=/var/www/fixmate/venv/bin"
EnvironmentFile=/var/www/fixmate/.env
ExecStart=/var/www/fixmate/venv/bin/gunicorn --workers 4 --bind 127.0.0.1:8000 wsgi:application

[Install]
WantedBy=multi-user.target
```
Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable fixmate
sudo systemctl start fixmate
```

### Step 4: Nginx Reverse Proxy Configuration (`/etc/nginx/sites-available/fixmate`)
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Static assets caching
    location /static/ {
        alias /var/www/fixmate/app/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # Proxy to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
Enable Nginx site and test config:
```bash
sudo ln -s /etc/nginx/sites-available/fixmate /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 4. Deploying to Render / Railway (PaaS)

FixMate contains a `Procfile` ready for one-click deployment:
```text
web: gunicorn wsgi:application
```
1. Connect GitHub repository to Render / Railway.
2. Add a managed MySQL database add-on.
3. Configure `DATABASE_URL` and `SECRET_KEY` in environment variables.
4. Set build command: `pip install -r requirements.txt && flask db upgrade`.
5. Set start command: `gunicorn wsgi:application`.

