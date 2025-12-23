#!/bin/bash
# Quick diagnostic and fix script - Run this on your EC2 instance

echo "====================================="
echo "Document Management Service Diagnostics"
echo "====================================="

# Check current directory
echo -e "\n📁 Current Directory:"
pwd
ls -la

# Check if running
echo -e "\n🔍 Checking if service is running:"
ps aux | grep uvicorn | grep -v grep || echo "❌ Service NOT running"

# Check ports
echo -e "\n🔌 Checking ports:"
sudo netstat -tulpn | grep -E '8000|5432' || echo "❌ Ports not listening"

# Check IAM role
echo -e "\n🔐 Checking IAM role:"
curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/iam/security-credentials/ || echo "❌ No IAM role attached"

# Check S3 access
echo -e "\n☁️ Checking S3 access:"
aws s3 ls s3://my-doc-storage-prod/ 2>&1 | head -3 || echo "❌ Cannot access S3 bucket"

# Check PostgreSQL
echo -e "\n🗄️ Checking PostgreSQL:"
sudo systemctl status postgresql --no-pager || echo "❌ PostgreSQL not running"

# Check Python
echo -e "\n🐍 Checking Python:"
python3 --version
which python3

# Quick fix: Start application manually
echo -e "\n🚀 Starting application manually..."
echo "This will run in foreground. Press Ctrl+C to stop."
echo -e "\nStarting in 3 seconds..."
sleep 3

cd /var/www/docmanagement 2>/dev/null || cd ~/backend\ service || cd .
source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate
pip install --quiet uvicorn fastapi 2>/dev/null

echo "Starting uvicorn on port 8000..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
