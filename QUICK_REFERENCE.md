# Quick Reference Card

## Essential Commands

### Start the Service
```bash
docker-compose up -d              # Start all services
docker-compose logs -f app        # View logs
```

### Stop the Service
```bash
docker-compose down               # Stop all services
docker-compose down -v            # Stop and remove data volumes
```

### Development
```bash
uvicorn app.main:app --reload     # Run with auto-reload
alembic upgrade head              # Run migrations
alembic revision --autogenerate   # Create new migration
pytest                            # Run tests
black app/                        # Format code
```

---

## API Endpoints Quick Reference

### Base URL
```
http://localhost:8000
```

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login (get tokens) |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | Revoke refresh token |
| GET | `/api/v1/auth/me` | Get current user |

### Documents

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| POST | `/api/v1/documents` | Upload document | Authenticated |
| GET | `/api/v1/documents` | List documents | Authenticated |
| GET | `/api/v1/documents/{id}` | Get metadata | READ |
| PUT | `/api/v1/documents/{id}` | Update metadata | EDIT |
| DELETE | `/api/v1/documents/{id}` | Delete document | ADMIN |
| GET | `/api/v1/documents/{id}/download` | Download file | READ |
| GET | `/api/v1/documents/{id}/versions` | Version history | READ |
| POST | `/api/v1/documents/{id}/upload-version` | New version | EDIT |

### Permissions

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| POST | `/api/v1/documents/{id}/permissions` | Share document | ADMIN |
| GET | `/api/v1/documents/{id}/permissions` | List permissions | READ |
| PUT | `/api/v1/documents/{id}/permissions/{user_id}` | Update permission | ADMIN |
| DELETE | `/api/v1/documents/{id}/permissions/{user_id}` | Revoke access | ADMIN |

---

## cURL Examples

### 1. Register
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

### 3. Upload Document
```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "title=My Document" \
  -F "file=@document.pdf"
```

### 4. List Documents
```bash
curl http://localhost:8000/api/v1/documents?page=1&limit=20 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 5. Download Document
```bash
curl http://localhost:8000/api/v1/documents/DOCUMENT_ID/download \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 6. Share Document
```bash
curl -X POST http://localhost:8000/api/v1/documents/DOC_ID/permissions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "USER_ID",
    "role": "EDIT"
  }'
```

---

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@localhost/db` |
| `SECRET_KEY` | JWT signing key (min 32 chars) | `your-secret-key...` |
| `S3_BUCKET_NAME` | S3 bucket name | `document-storage-bucket` |
| `AWS_ACCESS_KEY_ID` | AWS/MinIO access key | `minioadmin` |
| `AWS_SECRET_ACCESS_KEY` | AWS/MinIO secret key | `minioadmin` |
| `S3_ENDPOINT_URL` | S3 endpoint (for MinIO) | `http://localhost:9000` |
| `MAX_UPLOAD_SIZE` | Max file size in bytes | `104857600` (100MB) |
| `ALLOWED_EXTENSIONS` | Comma-separated file types | `pdf,docx,jpg,png` |

---

## Docker Compose Services

| Service | Port | Description |
|---------|------|-------------|
| `app` | 8000 | FastAPI application |
| `postgres` | 5432 | PostgreSQL database |
| `minio` | 9000 | MinIO S3-compatible storage (API) |
| `minio` | 9001 | MinIO console (Web UI) |

---

## Database Access

```bash
# Connect to PostgreSQL
docker exec -it docmanagement-postgres psql -U postgres -d docmanagement

# Useful queries
SELECT * FROM users;
SELECT * FROM documents WHERE owner_id = 'USER_UUID';
SELECT * FROM document_versions ORDER BY created_at DESC LIMIT 10;
SELECT * FROM document_permissions WHERE document_id = 'DOC_UUID';
```

---

## Permission Roles

| Role | Can Do |
|------|--------|
| **READ** | View metadata, download files, see versions |
| **EDIT** | All READ + update metadata, upload new versions |
| **ADMIN** | All EDIT + manage permissions, delete document |
| **OWNER** | Implicit ADMIN (cannot be revoked) |

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 204 | Success (no content) |
| 400 | Bad request (validation error) |
| 401 | Unauthorized (missing/invalid token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not found |
| 409 | Conflict (e.g., duplicate email) |
| 413 | File too large |
| 422 | Unprocessable entity (Pydantic validation) |
| 500 | Internal server error |

---

## File Locations

| Path | Contains |
|------|----------|
| `app/` | Application code |
| `alembic/versions/` | Database migrations |
| `tests/` | Test files |
| `.env` | Environment configuration |
| `requirements.txt` | Python dependencies |
| `docker-compose.yml` | Service definitions |
| `logs/` | Application logs |

---

## Helpful Links

- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **MinIO Console**: http://localhost:9001 (admin/admin)

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Port 8000 in use | Change `PORT` in `.env` or kill process |
| Database connection failed | `docker-compose up -d postgres` |
| S3 upload failed | `docker-compose up -d minio` |
| Import errors | Activate venv: `source venv/bin/activate` |
| Migration failed | Check database is running, verify `DATABASE_URL` |

---

## Testing

```bash
pytest                          # Run all tests
pytest tests/test_auth.py       # Run specific file
pytest -v                       # Verbose output
pytest --cov=app                # With coverage
pytest -k "test_login"          # Run tests matching pattern
```

---

## Code Quality

```bash
black app/                      # Format code
isort app/                      # Sort imports
flake8 app/                     # Lint
mypy app/ --ignore-missing-imports  # Type check
```

---

## Migration Commands

```bash
alembic upgrade head            # Apply all migrations
alembic downgrade -1            # Rollback one migration
alembic history                 # View migration history
alembic current                 # Show current revision
alembic revision -m "message"   # Create empty migration
alembic revision --autogenerate -m "message"  # Auto-generate
```

---

## Production Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Generate strong `SECRET_KEY` (32+ chars)
- [ ] Use managed PostgreSQL
- [ ] Use real AWS S3
- [ ] Configure CORS origins
- [ ] Set `DEBUG=false`
- [ ] Enable HTTPS/TLS
- [ ] Set up monitoring
- [ ] Configure backups
- [ ] Run security scan

---

**For full documentation, see:**
- [README.md](README.md) - Overview
- [GETTING_STARTED.md](GETTING_STARTED.md) - Setup guide
- [DESIGN.md](DESIGN.md) - Architecture
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - What we built
