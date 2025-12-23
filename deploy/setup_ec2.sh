#!/bin/bash
# EC2 Setup Script for Document Management Service

set -e  # Exit on error

echo "====================================="
echo "EC2 Deployment Setup"
echo "====================================="

# Update system
echo "Step 1: Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3.11
echo "Step 2: Installing Python 3.11..."
sudo apt-get install -y python3.11 python3.11-venv python3-pip python3.11-dev

# Install PostgreSQL
echo "Step 3: Installing PostgreSQL..."
sudo apt-get install -y postgresql postgresql-contrib

# Install other dependencies
echo "Step 4: Installing system dependencies..."
sudo apt-get install -y build-essential libpq-dev git nginx

# Install AWS CLI
echo "Step 5: Installing AWS CLI..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
sudo apt-get install -y unzip
unzip awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip

# Create application directory
echo "Step 6: Creating application directory..."
sudo mkdir -p /var/www/docmanagement
sudo chown -R ubuntu:ubuntu /var/www/docmanagement

echo "====================================="
echo "System setup complete!"
echo "Next steps:"
echo "1. Upload your application code to /var/www/docmanagement"
echo "2. Run setup_app.sh"
echo "====================================="
