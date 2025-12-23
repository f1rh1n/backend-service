# Getting Started Guide

## Quick Start (5 Minutes)

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Git

### Step 1: Clone and Setup

```bash
# Navigate to the project directory
cd "backend service"

# Copy environment file
cp .env.example .env
```

### Step 2: Start with Docker Compose (Recommended)

```bash
# Start all services (PostgreSQL, MinIO, App)
docker-compose up -d

# View logs
docker-compose logs -f app

# The API will be available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

That's it! The service is now running.

---

## Manual Setup (For Development)

### Step 1: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Start Dependencies

```bash
# Start PostgreSQL and MinIO
docker-compose up -d postgres minio
```

### Step 4: Configure Environment

Edit `.env` file with your settings. Key variables:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/docmanagement
SECRET_KEY=your-super-secret-key-min-32-characters
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
S3_BUCKET_NAME=document-storage-bucket
S3_ENDPOINT_URL=http://localhost:9000
```

### Step 5: Run Migrations

```bash
alembic upgrade head
```

### Step 6: Start Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

---

## Using the API

### 1. Register a User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepass123",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=securepass123"
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

Save the `access_token` for subsequent requests.

### 3. Upload a Document

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "title=My Document" \
  -F "description=A test document" \
  -F "tags=test" \
  -F "tags=demo" \
  -F "file=@/path/to/your/file.pdf"
```

### 4. List Documents

```bash
curl http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 5. Share a Document

```bash
curl -X POST http://localhost:8000/api/v1/documents/DOCUMENT_ID/permissions \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "USER_ID_TO_SHARE_WITH",
    "role": "READ"
  }'
```

---

## Interactive API Documentation

Visit http://localhost:8000/docs for Swagger UI where you can:
- See all available endpoints
- Test API calls interactively
- View request/response schemas
- Authenticate and make authorized requests

Alternative documentation: http://localhost:8000/redoc

---

## Running Tests

```bash
# Install test dependencies (already in requirements.txt)
pip install pytest pytest-asyncio pytest-cov httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run in verbose mode
pytest -v
```

---

## Development Workflow

### 1. Make Code Changes

Edit files in the `app/` directory. With `--reload` flag, uvicorn automatically restarts.

### 2. Database Changes

```bash
# Create a new migration
alembic revision --autogenerate -m "Add new column"

# Review the generated migration in alembic/versions/

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### 3. Code Quality

```bash
# Format code
black app/
isort app/

# Lint
flake8 app/

# Type check
mypy app/ --ignore-missing-imports
```

---

## Useful Commands

### Docker

```bash
# View logs
docker-compose logs -f app

# Restart service
docker-compose restart app

# Stop all services
docker-compose down

# Remove all data (databases, S3 files)
docker-compose down -v

# Rebuild app image
docker-compose build app
```

### Database

```bash
# Connect to PostgreSQL
docker exec -it docmanagement-postgres psql -U postgres -d docmanagement

# Useful SQL queries
SELECT * FROM users;
SELECT * FROM documents;
SELECT * FROM document_versions;
SELECT * FROM document_permissions;
```

### MinIO (S3)

Access MinIO console at http://localhost:9001
- Username: minioadmin
- Password: minioadmin

---

## Troubleshooting

### Problem: "Database connection failed"

**Solution**: Ensure PostgreSQL is running
```bash
docker-compose up -d postgres
# Wait 5 seconds for it to start
```

### Problem: "S3 upload failed"

**Solution**: Ensure MinIO is running and bucket is created
```bash
docker-compose up -d minio minio-init
```

### Problem: "Import errors in Python"

**Solution**: Ensure virtual environment is activated and dependencies installed
```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Problem: "Port 8000 already in use"

**Solution**: Change port in `.env` or kill the process using port 8000
```bash
# Find process
lsof -i :8000  # Mac/Linux
netstat -ano | findstr :8000  # Windows

# Kill it or change PORT in .env
```

---

## Production Deployment

### Environment Setup

1. Set `ENVIRONMENT=production` in `.env`
2. Generate strong `SECRET_KEY`:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
3. Use managed PostgreSQL (AWS RDS, Azure Database, etc.)
4. Use real AWS S3 (or compatible service)
5. Set proper `BACKEND_CORS_ORIGINS`
6. Set `DEBUG=false`

### Docker Production Build

```bash
# Build production image
docker build -t docmanagement:latest .

# Run with production settings
docker run -p 8000:8000 --env-file .env.production docmanagement:latest
```

### Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Health Monitoring

```bash
# Check health endpoint
curl http://localhost:8000/health

# Expected response
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "dependencies": {
    "database": "up",
    "s3": "up"
  }
}
```

---

## Next Steps

1. **Read the Design Document**: See [DESIGN.md](DESIGN.md) for architecture details
2. **Explore the API**: Use Swagger UI at `/docs`
3. **Run Tests**: `pytest` to see examples of API usage
4. **Check Implementation Status**: See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)
5. **Deploy**: Follow deployment checklist in DESIGN.md

---

## Support

For issues or questions:
- Check the [README.md](README.md)
- Review [DESIGN.md](DESIGN.md) for architecture questions
- Open an issue on GitHub
