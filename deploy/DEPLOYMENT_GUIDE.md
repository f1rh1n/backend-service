# EC2 Deployment Guide

## Prerequisites

Before you begin, ensure you have:
- ✅ EC2 instance running (Ubuntu 22.04 or later)
- ✅ SSH access to EC2 instance
- ✅ S3 bucket created (`my-doc-storage-prod` in `ap-south-1`)
- ✅ IAM role for EC2 with S3 access

---

## Step-by-Step Deployment

### 1. Configure AWS (On your local machine)

**Create IAM Role:**

1. Go to AWS Console → IAM → Roles
2. Click "Create role"
3. Choose "AWS service" → "EC2"
4. Click "Next"
5. Click "Create policy" → JSON tab
6. Paste the contents from `deploy/iam_policy.json`
7. Name it: `DocManagement-S3-Access`
8. Go back and attach this policy
9. Name the role: `DocManagement-EC2-Role`
10. Create role

**Attach IAM Role to EC2:**

1. EC2 Console → Instances
2. Select your instance
3. Actions → Security → Modify IAM role
4. Select `DocManagement-EC2-Role`
5. Update IAM role

**Configure Security Group:**

1. EC2 Console → Security Groups
2. Select your instance's security group
3. Edit inbound rules:
   - Type: Custom TCP, Port: 8000, Source: 0.0.0.0/0 (or your IP)
   - Type: SSH, Port: 22, Source: Your IP
   - Type: PostgreSQL, Port: 5432, Source: sg-xxxxx (same security group)
4. Save rules

---

### 2. Upload Code to EC2

**Option A: Using SCP (from your local machine):**

```bash
# Compress your project (exclude venv, __pycache__, etc.)
cd "c:\Users\Farhan khan"
tar -czf docmanagement.tar.gz \
  --exclude="backend service/venv" \
  --exclude="backend service/__pycache__" \
  --exclude="backend service/.git" \
  --exclude="backend service/*.pyc" \
  "backend service"

# Upload to EC2
scp -i your-key.pem docmanagement.tar.gz ubuntu@YOUR-EC2-IP:~

# SSH into EC2 and extract
ssh -i your-key.pem ubuntu@YOUR-EC2-IP
sudo mkdir -p /var/www/docmanagement
sudo chown ubuntu:ubuntu /var/www/docmanagement
tar -xzf docmanagement.tar.gz -C /var/www/
mv /var/www/"backend service"/* /var/www/docmanagement/
```

**Option B: Using Git:**

```bash
ssh -i your-key.pem ubuntu@YOUR-EC2-IP
sudo mkdir -p /var/www/docmanagement
sudo chown ubuntu:ubuntu /var/www/docmanagement
cd /var/www/docmanagement
git clone YOUR_REPO_URL .
```

---

### 3. Run Setup Scripts (On EC2)

```bash
# SSH into EC2
ssh -i your-key.pem ubuntu@YOUR-EC2-IP

# Make scripts executable
cd /var/www/docmanagement/deploy
chmod +x *.sh

# 1. Setup system dependencies
./setup_ec2.sh

# 2. Setup application
./setup_app.sh

# 3. Edit .env file with your actual values
nano /var/www/docmanagement/.env

# Update these lines:
# DATABASE_URL=postgresql://docuser:your_secure_password_here@localhost:5432/docmanagement
# BACKEND_CORS_ORIGINS=["https://your-frontend.com"]

# 4. Setup systemd service
./setup_systemd.sh
```

---

### 4. Verify Deployment

```bash
# Check service status
sudo systemctl status docmanagement

# View logs
sudo journalctl -u docmanagement -f

# Test API locally
curl http://localhost:8000/health

# Test from your browser
http://YOUR-EC2-PUBLIC-IP:8000/docs
```

---

### 5. Create Database Tables

```bash
cd /var/www/docmanagement
source venv/bin/activate
alembic upgrade head
```

---

### 6. Test S3 Access

```bash
cd /var/www/docmanagement
source venv/bin/activate
python3 << 'EOF'
from app.s3_service import s3_service
print("Testing S3 connection...")
print("S3 client initialized successfully!")
EOF
```

---

## Troubleshooting

### Issue: Service won't start

```bash
# Check logs
sudo journalctl -u docmanagement -n 50 --no-pager

# Check if port is in use
sudo netstat -tulpn | grep 8000

# Restart service
sudo systemctl restart docmanagement
```

### Issue: Can't connect to database

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -U docuser -d docmanagement -h localhost

# Check DATABASE_URL in .env
cat /var/www/docmanagement/.env | grep DATABASE_URL
```

### Issue: S3 permission denied

```bash
# Verify IAM role is attached
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/

# Test S3 access
aws s3 ls s3://my-doc-storage-prod/

# Check bucket region matches .env
cat /var/www/docmanagement/.env | grep AWS_REGION
```

### Issue: Can't access from browser

```bash
# Check Security Group allows port 8000
# Check app is listening on 0.0.0.0 not 127.0.0.1
sudo netstat -tulpn | grep 8000

# Check if service is running
sudo systemctl status docmanagement
```

---

## Production Checklist

Before going live:

- [ ] Changed `SECRET_KEY` in `.env`
- [ ] Set `DEBUG=false`
- [ ] Updated `BACKEND_CORS_ORIGINS` with frontend URL
- [ ] Database password is secure
- [ ] IAM role attached to EC2
- [ ] Security Group configured
- [ ] S3 bucket created and accessible
- [ ] SSL/TLS certificate configured (optional but recommended)
- [ ] Database backups configured
- [ ] Monitoring/logging set up

---

## Useful Commands

```bash
# Service management
sudo systemctl start docmanagement
sudo systemctl stop docmanagement
sudo systemctl restart docmanagement
sudo systemctl status docmanagement

# View logs
sudo journalctl -u docmanagement -f
tail -f /var/log/docmanagement/error.log
tail -f /var/log/docmanagement/access.log

# Update application
cd /var/www/docmanagement
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart docmanagement

# Database migrations
cd /var/www/docmanagement
source venv/bin/activate
alembic upgrade head
```

---

## Optional: Setup Nginx Reverse Proxy

```bash
# Install nginx
sudo apt-get install nginx -y

# Create nginx config
sudo nano /etc/nginx/sites-available/docmanagement

# Paste this:
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Enable site
sudo ln -s /etc/nginx/sites-available/docmanagement /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Now access via: http://YOUR_DOMAIN_OR_IP/docs
```

---

## Support

If you encounter issues:

1. Check logs: `sudo journalctl -u docmanagement -n 100`
2. Verify environment: `cat /var/www/docmanagement/.env`
3. Test components individually (DB, S3, API)
4. Check Security Groups and IAM roles
