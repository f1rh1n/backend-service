# Collaborative Document Management Service

A production-grade, scalable backend service for collaborative document management with role-based access control, versioning, and S3 storage built with FastAPI.

## Features

- **Authentication & Authorization**: JWT-based OAuth2 authentication with role-based access control (READ, EDIT, ADMIN)
- **Document Management**: Upload, download, share, and delete documents
- **Versioning**: Immutable version history for all documents
- **Metadata Management**: Support for title, author, tags, upload date
- **Search & Filtering**: Indexed queries on metadata for high performance
- **Object Storage**: AWS S3 integration for scalable file storage
- **Relational Database**: PostgreSQL for metadata, permissions, and version history
- **Stateless Design**: Horizontally scalable architecture
- **Production Ready**: Comprehensive logging, error handling, rate limiting, security headers
- **Auto-Generated API Docs**: Interactive OpenAPI (Swagger) and ReDoc documentation

## Tech Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **ASGI Server**: Uvicorn
- **Database**: PostgreSQL 14+ with SQLAlchemy 2.0 (async)
- **Migrations**: Alembic
- **Object Storage**: AWS S3 (or S3-compatible like MinIO)
- **Authentication**: OAuth2 with JWT (python-jose)
- **Password Hashing**: Passlib with bcrypt
- **Validation**: Pydantic v2
- **Testing**: Pytest with async support
- **Code Quality**: Black, isort, flake8, mypy
- **Containerization**: Docker + Docker Compose

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ REST API
┌──────▼──────────────────────────────┐
│      FastAPI Application            │
│  ┌────────────────────────────────┐ │
│  │   Middleware Layer             │ │
│  │  - CORS, Auth, Rate Limiting   │ │
│  └────────────────────────────────┘ │
│  ┌────────────────────────────────┐ │
│  │   API Routes (Controllers)     │ │
│  │  - Pydantic Request/Response   │ │
│  └────────────────────────────────┘ │
│  ┌────────────────────────────────┐ │
│  │   Service Layer                │ │
│  │  - Business Logic              │ │
│  └────────────────────────────────┘ │
│  ┌────────────────────────────────┐ │
│  │   Repository Layer (CRUD)      │ │
│  │  - SQLAlchemy ORM              │ │
│  └────────────────────────────────┘ │
└──────┬──────────────────┬───────────┘
       │                  │
┌──────▼──────┐    ┌─────▼──────┐
│  PostgreSQL │    │   AWS S3   │
│  (Metadata) │    │  (Files)   │
└─────────────┘    └────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose
- PostgreSQL 14+ (or use Docker)
- AWS S3 bucket (or MinIO for local development)

### Installation

1. Clone the repository
```bash
git clone <repository-url>
cd backend-service
```

2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Start dependencies with Docker Compose
```bash
docker-compose up -d postgres minio
```

6. Run database migrations
```bash
alembic upgrade head
```

7. Start development server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

**Interactive API documentation:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user (returns access + refresh tokens)
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout (revoke refresh token)
- `GET /api/v1/auth/me` - Get current user info

### Documents
- `POST /api/v1/documents` - Upload document
- `GET /api/v1/documents` - List documents with search/filter/pagination
- `GET /api/v1/documents/{id}` - Get document metadata
- `GET /api/v1/documents/{id}/download` - Download document (presigned URL)
- `PUT /api/v1/documents/{id}` - Update document metadata
- `POST /api/v1/documents/{id}/upload-version` - Upload new version
- `DELETE /api/v1/documents/{id}` - Soft delete document
- `GET /api/v1/documents/{id}/versions` - Get version history
- `GET /api/v1/documents/{id}/versions/{version_id}/download` - Download specific version

### Sharing & Permissions
- `POST /api/v1/documents/{id}/share` - Share document with user
- `GET /api/v1/documents/{id}/permissions` - List document permissions
- `PUT /api/v1/documents/{id}/permissions/{user_id}` - Update user permission
- `DELETE /api/v1/documents/{id}/permissions/{user_id}` - Revoke access

### Health & Monitoring
- `GET /health` - Health check endpoint
- `GET /metrics` - Application metrics (optional)

## Development

### Run tests
```bash
pytest                          # Run all tests
pytest --cov                    # Run with coverage
pytest -v                       # Verbose output
pytest tests/unit              # Run only unit tests
pytest tests/integration       # Run only integration tests
```

### Code quality
```bash
black .                         # Format code
isort .                         # Sort imports
flake8                         # Linting
mypy app                       # Type checking
```

### Database migrations
```bash
alembic revision --autogenerate -m "description"  # Create migration
alembic upgrade head                              # Apply migrations
alembic downgrade -1                              # Rollback one migration
alembic history                                   # View migration history
```

## Deployment

### Docker

Build and run with Docker:
```bash
docker build -t doc-management-service .
docker run -p 8000:8000 --env-file .env doc-management-service
```

Or use Docker Compose:
```bash
docker-compose up -d
```

### Production Configuration

For production deployment:

1. Set `ENVIRONMENT=production` in .env
2. Use a strong `SECRET_KEY` (min 32 characters)
3. Configure proper CORS origins
4. Set up proper logging aggregation
5. Use managed PostgreSQL (AWS RDS, etc.)
6. Use production S3 buckets with proper IAM policies
7. Set up SSL/TLS termination (reverse proxy like nginx)
8. Configure rate limiting appropriately
9. Set `DEBUG=false`

## Database Schema

### Core Tables
- `users` - User accounts and authentication
- `documents` - Document metadata
- `document_versions` - Immutable version history
- `document_tags` - Document tagging
- `document_permissions` - Role-based access control
- `refresh_tokens` - JWT refresh token management
- `activity_logs` - Audit trail

See [DESIGN.md](DESIGN.md) for detailed schema documentation.

## Security

- OAuth2 password flow with JWT access/refresh tokens
- Password hashing with bcrypt (cost factor 12)
- SQL injection prevention via SQLAlchemy ORM
- Input validation with Pydantic
- CORS protection
- Rate limiting
- File type and size validation
- Secure headers (via middleware)
- Presigned URLs for S3 access (temporary, scoped permissions)

## Performance & Scalability

- Async/await throughout (non-blocking I/O)
- Database connection pooling
- Indexed queries on frequently searched fields
- Pagination on all list endpoints
- Stateless design (can scale horizontally)
- Efficient file handling (streaming uploads/downloads)
- S3 presigned URLs (offload download traffic from app server)
- Lazy loading and eager loading strategies

## API Response Format

All API responses follow a consistent format:

**Success:**
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation successful"
}
```

**Error:**
```json
{
  "success": false,
  "error": "Error description",
  "detail": { ... }
}
```

**Paginated:**
```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "total": 100,
    "page": 1,
    "limit": 20,
    "total_pages": 5
  }
}
```

## Future Enhancements

See [DESIGN.md](DESIGN.md) for proposed future features including:
- Real-time collaboration with WebSockets
- Document comments and annotations
- Activity feeds and notifications
- Full-text search with Elasticsearch
- Document preview generation
- Advanced audit logging
- Multi-region replication
- GraphQL API
- Webhook notifications

## Environment Variables

See [.env.example](.env.example) for all configuration options.

## License

MIT

## Contributing

Pull requests welcome. Please ensure:
- All tests pass (`pytest`)
- Code is formatted (`black`, `isort`)
- Type hints are correct (`mypy`)
- Documentation is updated
