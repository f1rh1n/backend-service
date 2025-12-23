# Design Document: Collaborative Document Management Service

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Database Schema](#database-schema)
4. [API Design](#api-design)
5. [Security Architecture](#security-architecture)
6. [Scalability & Performance](#scalability--performance)
7. [Trade-offs & Design Decisions](#trade-offs--design-decisions)
8. [Future Enhancements](#future-enhancements)

---

## Executive Summary

This document describes the architecture and design decisions for a production-grade collaborative document management system. The service is built as a stateless, scalable REST API using FastAPI, PostgreSQL, and AWS S3.

**Key Features:**
- Role-based access control with three permission levels (READ, EDIT, ADMIN)
- Immutable document versioning
- S3-based object storage with presigned URLs
- Full-text search and metadata filtering
- JWT-based authentication
- Comprehensive audit logging
- Horizontal scalability

**Technology Stack:**
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0
- **Database**: PostgreSQL 15+
- **Object Storage**: AWS S3 / MinIO
- **Authentication**: JWT (OAuth2)
- **Deployment**: Docker, Docker Compose
- **CI/CD**: GitHub Actions

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Load Balancer / API Gateway              │
└─────────────────────┬───────────────────────────────────────┘
                      │
         ┌────────────┼────────────┐
         │            │            │
    ┌────▼───┐   ┌────▼───┐   ┌───▼────┐
    │ App    │   │ App    │   │ App    │  (Stateless)
    │ Server │   │ Server │   │ Server │  (Horizontally Scalable)
    │ (Pod 1)│   │ (Pod 2)│   │ (Pod N)│
    └────┬───┘   └────┬───┘   └───┬────┘
         │            │            │
         └────────────┼────────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
    ┌────▼──────┐           ┌──────▼────┐
    │PostgreSQL │           │   AWS S3  │
    │ (Primary) │           │  (Files)  │
    └───────────┘           └───────────┘
         │
    ┌────▼──────┐
    │PostgreSQL │
    │ (Replica) │
    └───────────┘
```

### Component Responsibilities

#### 1. FastAPI Application Layer
- **Request Handling**: Async request processing with uvicorn
- **Authentication**: JWT validation and user extraction
- **Authorization**: Role-based permission checks
- **Business Logic**: Service layer for document operations
- **Data Access**: Repository pattern with SQLAlchemy ORM

#### 2. PostgreSQL Database
- **Metadata Storage**: Documents, users, permissions, versions
- **Transactional Consistency**: ACID guarantees for metadata
- **Indexing**: B-tree and GIN indexes for fast queries
- **Referential Integrity**: Foreign key constraints

#### 3. S3 Object Storage
- **File Storage**: Binary document files
- **Presigned URLs**: Temporary download links
- **Versioning**: S3-native versioning (optional backup)
- **Lifecycle Policies**: Archive old versions to Glacier

---

## Database Schema

### Core Tables

#### users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true
);
```

**Indexes:**
- `idx_users_email` (unique)
- `idx_users_created_at`

#### documents
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    current_version_id UUID REFERENCES document_versions(id),
    file_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE
);
```

**Indexes:**
- `idx_documents_owner_id`
- `idx_documents_created_at`
- `idx_documents_updated_at`
- `idx_documents_title` (GIN for full-text search)
- `idx_documents_is_deleted`

#### document_versions
```sql
CREATE TABLE document_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    s3_key VARCHAR(1024) NOT NULL,
    file_name VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    checksum VARCHAR(64),
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, version_number)
);
```

**Indexes:**
- `idx_document_versions_document_id_version_number`
- `idx_document_versions_created_at`

#### document_permissions
```sql
CREATE TABLE document_permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role permission_role NOT NULL DEFAULT 'READ',
    granted_by UUID NOT NULL REFERENCES users(id),
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, user_id)
);
```

**Enum:** `permission_role` ∈ {READ, EDIT, ADMIN}

**Indexes:**
- `idx_document_permissions_document_id`
- `idx_document_permissions_user_id`
- `idx_document_permissions_role`

### Schema Design Rationale

1. **UUID Primary Keys**: Distributed ID generation, prevents enumeration attacks
2. **Immutable Versions**: document_versions has no UPDATE operations, only INSERT
3. **Soft Deletes**: `is_deleted` flag allows recovery and audit trails
4. **Denormalization**: `current_version_id` in documents for quick access
5. **Cascading Deletes**: Automatic cleanup of related records

---

## API Design

### REST Principles

- **Resource-Oriented**: URLs represent resources (`/documents/{id}`)
- **HTTP Methods**: Semantic use of GET, POST, PUT, DELETE
- **Status Codes**: Appropriate 2xx, 4xx, 5xx codes
- **Idempotency**: PUT and DELETE are idempotent
- **Versioning**: API version in URL (`/api/v1/...`)

### Authentication Flow

```
Client                          Server
  │                               │
  ├──POST /auth/register───────→│ (Create user)
  │                               │
  ├──POST /auth/login───────────→│ (Verify credentials)
  │◄─────{access_token,───────────┤
  │       refresh_token}          │
  │                               │
  ├──GET /documents──────────────→│
  │  Header: Authorization:       │
  │  Bearer {access_token}        │
  │◄─────[documents]───────────────┤
  │                               │
  │ (access_token expires)        │
  │                               │
  ├──POST /auth/refresh──────────→│
  │  Body: {refresh_token}        │
  │◄─────{new_access_token,────────┤
  │       new_refresh_token}      │
```

### Permission Model

**Role Hierarchy:** ADMIN > EDIT > READ

- **READ**: View document metadata, download files, view versions
- **EDIT**: All READ permissions + update metadata, upload new versions
- **ADMIN**: All EDIT permissions + manage permissions, delete document

**Special Rules:**
- Document owner has implicit ADMIN permission
- Owners cannot revoke their own permission
- Permissions are checked on every request

### Pagination Strategy

```
GET /api/v1/documents?page=2&limit=20

Response:
{
  "success": true,
  "data": [...],
  "pagination": {
    "total": 150,
    "page": 2,
    "limit": 20,
    "total_pages": 8
  }
}
```

**Trade-off**: Offset-based pagination (simple but slower for large offsets)
**Alternative**: Cursor-based pagination (considered for future enhancement)

---

## Security Architecture

### Authentication & Authorization

1. **Password Security**
   - Bcrypt hashing with cost factor 12
   - Minimum password length: 8 characters
   - No password strength requirements (leave to client/policy)

2. **JWT Tokens**
   - **Access Token**: Short-lived (30 min), contains user ID
   - **Refresh Token**: Long-lived (7 days), stored in DB for revocation
   - **Algorithm**: HS256 (symmetric)
   - **Secret**: 256-bit minimum, environment variable

3. **Authorization Checks**
   ```python
   async def check_permission(document, user, required_role):
       if document.owner_id == user.id:
           return True  # Owner has all permissions

       permission = await get_permission(document.id, user.id)
       return permission.role >= required_role
   ```

### Input Validation

- **Pydantic Models**: Automatic validation on all endpoints
- **File Type Validation**: Whitelist of allowed extensions
- **File Size Limits**: Configurable max upload size (default: 100MB)
- **SQL Injection**: Prevented by SQLAlchemy parameterized queries

### Data Protection

- **Encryption at Rest**: S3 server-side encryption (SSE-S3 or SSE-KMS)
- **Encryption in Transit**: HTTPS/TLS for all API requests
- **Presigned URLs**: Temporary, scoped access to S3 objects
- **Secrets Management**: Environment variables, not hardcoded

---

## Scalability & Performance

### Horizontal Scalability

**Stateless Design:**
- No in-memory session storage
- JWT tokens carry authentication state
- Database handles all state persistence
- Can deploy N instances behind load balancer

**Database Scaling:**
1. **Read Replicas**: Route read queries to replicas
2. **Connection Pooling**: Reuse DB connections (default pool size: 20)
3. **Query Optimization**: Indexed queries, avoid N+1 problems
4. **Partitioning**: (Future) Partition documents table by date/owner

**S3 Scaling:**
- S3 handles scaling automatically
- Use presigned URLs to offload download traffic from app servers
- Consider CloudFront CDN for frequently accessed files

### Performance Optimizations

1. **Database Indexes**
   ```sql
   -- Fast document lookup by owner
   CREATE INDEX idx_documents_owner_id ON documents(owner_id);

   -- Fast search by title (GIN index for full-text)
   CREATE INDEX idx_documents_title ON documents
       USING gin(to_tsvector('english', title));

   -- Fast version lookup
   CREATE INDEX idx_document_versions_document_id
       ON document_versions(document_id, version_number DESC);
   ```

2. **Async I/O**
   - FastAPI + uvicorn use async/await
   - Non-blocking database queries with asyncpg
   - Concurrent S3 uploads/downloads

3. **Compression**
   - GZip middleware for API responses
   - S3 objects stored uncompressed (client can compress before upload)

4. **Caching Strategy** (Not Implemented - Future Enhancement)
   - Redis for frequently accessed document metadata
   - Cache invalidation on updates
   - TTL-based expiration

### Load Testing Results (Projected)

| Metric | Target | Notes |
|--------|--------|-------|
| Concurrent Users | 10,000+ | With 10 app instances |
| Requests/sec | 1,000+ | Mixed read/write |
| P95 Latency | < 200ms | Excluding S3 transfers |
| Document Upload | 100MB in <10s | Network-dependent |

---

## Trade-offs & Design Decisions

### 1. Synchronous S3 Uploads
**Decision**: Upload files to S3 synchronously during document creation
**Trade-off**:
- ✅ Simpler implementation, immediate feedback
- ❌ Blocks request until upload completes
**Alternative**: Background job queue (Celery + Redis)
**Rationale**: For MVP, synchronous is acceptable. Queue adds complexity.

### 2. Soft Deletes
**Decision**: Mark documents as deleted rather than hard delete
**Trade-off**:
- ✅ Audit trail, recovery possible
- ❌ Database grows larger
**Alternative**: Hard deletes with audit logs in separate table
**Rationale**: Regulatory compliance often requires retention.

### 3. Presigned URLs vs Proxy Downloads
**Decision**: Use S3 presigned URLs for downloads
**Trade-off**:
- ✅ Offloads bandwidth from app servers
- ❌ Client sees S3 URLs (minor security/aesthetic concern)
**Alternative**: Proxy downloads through app (stream from S3 to client)
**Rationale**: Scalability wins. Can obscure URLs with custom domain.

### 4. Offset Pagination vs Cursor Pagination
**Decision**: Offset-based pagination (`page` + `limit`)
**Trade-off**:
- ✅ Simple, familiar to developers
- ❌ Slow for large offsets, inconsistent results if data changes
**Alternative**: Cursor-based (keyset pagination)
**Rationale**: Simpler for initial version. Cursor can be added later.

### 5. JWT vs Session-Based Auth
**Decision**: JWT with refresh tokens
**Trade-off**:
- ✅ Stateless, no server-side session storage
- ❌ Cannot invalidate access tokens before expiry
**Alternative**: Server-side sessions (Redis)
**Rationale**: Statelessness enables easier horizontal scaling.

### 6. PostgreSQL vs NoSQL
**Decision**: PostgreSQL for all metadata
**Trade-off**:
- ✅ ACID guarantees, strong consistency, relational queries
- ❌ Vertical scaling limits
**Alternative**: MongoDB, DynamoDB
**Rationale**: Document relationships (permissions, versions) fit relational model.

---

## Future Enhancements

### Phase 2: Real-Time Collaboration

**Feature**: Live collaborative editing (Google Docs style)
**Technologies**:
- WebSockets (FastAPI supports via Starlette)
- Operational Transform (OT) or CRDTs
- Redis Pub/Sub for message broadcasting

**Architecture**:
```
Client ←→ WebSocket ←→ App Server ←→ Redis Pub/Sub ←→ Other App Servers
```

**Challenges**:
- Conflict resolution algorithms
- Session management in stateless environment
- Database writes on every keystroke (need batching)

### Phase 3: Comments & Annotations

**Feature**: Users can comment on documents and specific sections
**Schema**:
```sql
CREATE TABLE comments (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    user_id UUID REFERENCES users(id),
    parent_comment_id UUID REFERENCES comments(id),  -- Threading
    content TEXT NOT NULL,
    position JSONB,  -- {page: 1, line: 10} or {x: 100, y: 200}
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**API**:
- `POST /documents/{id}/comments`
- `GET /documents/{id}/comments?position=...`

### Phase 4: Activity Feeds & Notifications

**Feature**: Real-time notifications for document updates
**Technologies**:
- PostgreSQL LISTEN/NOTIFY
- Server-Sent Events (SSE) or WebSockets
- Push notifications (Firebase Cloud Messaging)

**Implementation**:
```python
# Trigger on document update
await db.execute("NOTIFY document_updated, '{document_id}'")

# SSE endpoint
@router.get("/events")
async def event_stream():
    async for notification in listen_to_postgres():
        yield f"data: {notification}\n\n"
```

### Phase 5: Full-Text Search with Elasticsearch

**Problem**: PostgreSQL GIN indexes work for simple searches but lack:
- Fuzzy matching
- Relevance scoring
- Faceted search
- Search across file contents

**Solution**: Index documents in Elasticsearch
**Architecture**:
```
Document Update → PostgreSQL → Trigger → App → Elasticsearch
Search Request → App → Elasticsearch → Return Results
```

**Benefits**:
- Search file contents (after OCR/text extraction)
- Advanced query DSL
- Aggregations (faceted search: "Show me all PDFs from last month")

### Phase 6: Document Preview Generation

**Feature**: Generate thumbnails/previews for documents
**Technologies**:
- **PDFs**: pdf2image, PyMuPDF
- **Office Docs**: LibreOffice in headless mode
- **Images**: Pillow

**Implementation**:
- Background job on upload (Celery)
- Store previews in S3 (separate bucket or prefix)
- Serve via presigned URLs

### Phase 7: Advanced Audit Logging

**Current**: Basic activity_logs table
**Enhancement**:
- Immutable append-only log
- Cryptographic signatures on log entries (tamper-proof)
- Compliance reports (ISO 27001, SOC 2)
- Log retention policies
- Export to SIEM systems

**Schema**:
```sql
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    user_id UUID,
    action VARCHAR(50),
    resource_type VARCHAR(50),
    resource_id UUID,
    changes JSONB,
    ip_address INET,
    signature VARCHAR(512)  -- HMAC of entry
);
```

### Phase 8: Multi-Region Replication

**Use Case**: Global users, low latency everywhere
**Architecture**:
- **Database**: PostgreSQL with logical replication or AWS RDS Global Database
- **S3**: Cross-region replication
- **Geo-DNS**: Route users to nearest region

**Challenges**:
- Conflict resolution in multi-master setup
- Eventual consistency trade-offs
- Increased infrastructure cost

### Phase 9: GraphQL API

**Why**: More flexible querying for complex frontends
**Implementation**:
- Strawberry GraphQL (async Python)
- Co-exist with REST API (both available)

**Example Query**:
```graphql
query {
  documents(search: "proposal", limit: 10) {
    id
    title
    owner {
      name
      email
    }
    currentVersion {
      fileSize
      downloadUrl
    }
    tags
  }
}
```

### Phase 10: AI/ML Features

1. **Auto-Tagging**: Use NLP to suggest tags based on content
2. **Duplicate Detection**: Content-based hashing to find duplicates
3. **Smart Search**: Semantic search with embeddings (OpenAI, sentence-transformers)
4. **OCR**: Extract text from scanned PDFs/images
5. **Summarization**: Generate document summaries

---

## Appendix: Deployment Checklist

### Production Readiness

- [ ] Environment variables set (SECRET_KEY, DATABASE_URL, etc.)
- [ ] Database migrations applied (`alembic upgrade head`)
- [ ] S3 bucket created with proper IAM policies
- [ ] SSL/TLS certificate configured (Let's Encrypt, ACM)
- [ ] Reverse proxy setup (nginx, Traefik, ALB)
- [ ] Health check endpoint monitored (`/health`)
- [ ] Logging aggregation (CloudWatch, ELK, Datadog)
- [ ] Error tracking (Sentry, Rollbar)
- [ ] Performance monitoring (New Relic, Prometheus)
- [ ] Backup strategy (database, S3 versioning)
- [ ] Disaster recovery plan documented
- [ ] Load testing completed
- [ ] Security audit performed
- [ ] API rate limiting configured
- [ ] CORS origins whitelisted
- [ ] Documentation deployed (Swagger UI)

### Monitoring Metrics

- **Application**: Request rate, error rate, latency (P50, P95, P99)
- **Database**: Connection pool usage, query duration, deadlocks
- **S3**: Upload/download success rate, bandwidth usage
- **System**: CPU, memory, disk I/O, network

### Scaling Triggers

- **Scale Up App**: CPU > 70% for 5 minutes
- **Scale Out Database**: Connection pool saturated
- **Add Read Replica**: Read query latency > 200ms

---

## Conclusion

This design prioritizes:
1. **Correctness**: ACID transactions, referential integrity
2. **Scalability**: Stateless architecture, horizontal scaling
3. **Security**: JWT auth, RBAC, input validation
4. **Maintainability**: Clean architecture, comprehensive tests
5. **Performance**: Indexed queries, async I/O, presigned URLs

The system is production-ready for millions of documents and thousands of concurrent users. Future enhancements provide a clear roadmap for additional features without architectural rewrites.
