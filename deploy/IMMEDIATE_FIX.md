# IMMEDIATE FIX - Get Your API Running NOW

Since you're already on EC2 and uvicorn is not running, follow these steps to get it started immediately:

## 🚀 Quick Start (5 minutes)

### Step 1: Find your application code

```bash
# Check if code is in /var/www/docmanagement
ls /var/www/docmanagement

# OR check home directory
ls ~/backend*
ls ~/*backend*

# Once found, cd into it
cd /var/www/docmanagement  # or wherever your code is
```

### Step 2: Install dependencies

```bash
# Install Python if needed
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Step 3: Fix .env file

```bash
# Edit .env file
nano .env

# Make these changes:
# 1. Remove or comment out this line:
#    S3_ENDPOINT_URL=http://localhost:9000

# 2. Make sure these are NOT set (or comment them out):
#    # AWS_ACCESS_KEY_ID=
#    # AWS_SECRET_ACCESS_KEY=

# 3. Ensure this is set:
#    S3_BUCKET_NAME=my-doc-storage-prod
#    AWS_REGION=ap-south-1

# Save: Ctrl+X, Y, Enter
```

### Step 4: Setup database

```bash
# Install PostgreSQL
sudo apt-get install -y postgresql

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database
sudo -u postgres psql << 'EOF'
CREATE DATABASE docmanagement;
CREATE USER docuser WITH ENCRYPTED PASSWORD 'docpass123';
GRANT ALL PRIVILEGES ON DATABASE docmanagement TO docuser;
\c docmanagement
GRANT ALL ON SCHEMA public TO docuser;
EOF

# Update .env with database URL
nano .env
# Change DATABASE_URL to:
# DATABASE_URL=postgresql://docuser:docpass123@localhost:5432/docmanagement
```

### Step 5: Run migrations

```bash
source venv/bin/activate
alembic upgrade head
```

### Step 6: Start the application

```bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 7: Test it

Open a new terminal and run:
```bash
curl http://localhost:8000/health
```

Or from your browser:
```
http://YOUR-EC2-PUBLIC-IP:8000/docs
```

---

## If Still Not Working...

### Check Security Group

1. Go to AWS Console → EC2 → Instances
2. Click your instance → Security tab
3. Click the Security Group link
4. Inbound rules → Edit
5. Add rule: Type=Custom TCP, Port=8000, Source=0.0.0.0/0
6. Save

### Check IAM Role

```bash
# This should return role name:
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/

# If blank, attach IAM role:
# 1. EC2 Console → select instance
# 2. Actions → Security → Modify IAM role
# 3. Select your S3 access role
```

### Check S3 Bucket

```bash
# Install AWS CLI
sudo apt-get install -y awscli

# Test S3 access
aws s3 ls s3://my-doc-storage-prod/

# If error, check:
# 1. Bucket exists in ap-south-1
# 2. IAM role has permissions
```

---

## 📝 Current Status

Based on your command output:
```
ubuntu@ip-172-31-9-97:~$ ps aux | grep uvicorn
ubuntu    391080  0.0  0.2   7076  2076 pts/0    S+   10:01   0:00 grep --color=auto uvicorn
```

This shows:
- ❌ Uvicorn is NOT running
- ✅ You're logged into EC2 as ubuntu
- ✅ You're in the home directory

---

## What To Do RIGHT NOW

Run these commands one by one:

```bash
# 1. Find your code
find ~ -name "app" -type d 2>/dev/null | grep -v venv

# 2. Go to the directory
cd <path-from-above>/..

# 3. Quick start
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn sqlalchemy asyncpg python-jose bcrypt python-multipart pydantic-settings alembic boto3
nano .env  # Fix S3_ENDPOINT_URL and AWS credentials
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Need Help?

Provide these outputs:
1. `pwd` - Where are you?
2. `ls -la` - What's in current directory?
3. `cat .env | grep -v SECRET | grep -v PASSWORD` - Environment config
4. `sudo systemctl status postgresql` - Database status
5. Error messages from uvicorn

Then I can provide specific fixes!
