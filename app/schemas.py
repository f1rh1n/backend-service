from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.models import PermissionRole


# Base Response
class APIResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data: Optional[dict] = None


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)


# Token Schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: UUID
    exp: datetime


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Document Schemas
class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class DocumentVersionResponse(BaseModel):
    id: UUID
    version_number: int
    file_name: str
    file_size: int
    mime_type: str
    created_by: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(DocumentBase):
    id: UUID
    owner_id: UUID
    file_type: str
    created_at: datetime
    updated_at: datetime
    current_version: Optional[DocumentVersionResponse] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    owner_id: UUID
    owner_name: str
    file_type: str
    file_size: int
    current_version: int
    tags: List[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentSearchParams(BaseModel):
    title: Optional[str] = None
    tags: Optional[List[str]] = None
    owner_id: Optional[UUID] = None
    file_type: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


# Permission Schemas
class PermissionCreate(BaseModel):
    user_id: UUID
    role: PermissionRole = PermissionRole.READ


class PermissionUpdate(BaseModel):
    role: PermissionRole


class PermissionResponse(BaseModel):
    id: UUID
    document_id: UUID
    user_id: UUID
    role: PermissionRole
    granted_by: UUID
    granted_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Upload Response
class UploadResponse(BaseModel):
    document_id: UUID
    version_id: UUID
    version_number: int
    file_name: str
    file_size: int
    s3_key: str


class DownloadResponse(BaseModel):
    url: str
    expires_in: int


# Pagination
class PaginationMeta(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int


class PaginatedResponse(BaseModel):
    success: bool = True
    data: List[dict]
    pagination: PaginationMeta
