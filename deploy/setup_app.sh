#!/bin/bash
# Application Setup Script

set -e

APP_DIR="/var/www/docmanagement"
cd $APP_DIR

echo "====================================="
echo "Setting up Application"
echo "====================================="

# Create virtual environment
echo "Step 1: Creating virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Step 2: Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Setup PostgreSQL database
echo "Step 3: Setting up PostgreSQL database..."
sudo -u postgres psql << EOF
CREATE DATABASE docmanagement;
CREATE USER docuser WITH ENCRYPTED PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE docmanagement TO docuser;
\c docmanagement
GRANT ALL ON SCHEMA public TO docuser;
EOF

# Update .env file
echo "Step 4: Configuring environment..."
cp .env.production .env

# Run database migrations
echo "Step 5: Running database migrations..."
source venv/bin/activate
alembic upgrade head

# Test S3 connection
echo "Step 6: Testing S3 connection..."
python3 << 'PYTHON_EOF'
import boto3
import sys

try:
    s3 = boto3.client('s3', region_name='ap-south-1')
    s3.head_bucket(Bucket='my-doc-storage-prod')
    print("✓ S3 bucket accessible!")
except Exception as e:
    print(f"✗ S3 error: {e}")
    print("Make sure IAM role is attached to EC2 instance")
    sys.exit(1)
PYTHON_EOF

echo "====================================="
echo "Application setup complete!"
echo "Next: Run setup_systemd.sh to configure auto-start"
echo "====================================="
