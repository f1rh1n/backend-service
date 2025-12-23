from sqlalchemy import (
    Column, String, Integer, BigInteger, Boolean, DateTime, ForeignKey,
    Text, Enum as SQLEnum, Index, CheckConstraint, UniqueConstraint, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid
import enum

from app.database import Base


# Enums
class PermissionRole(str, enum.Enum):
    READ = "READ"
    EDIT = "EDIT"
    ADMIN = "ADMIN"


# Models
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    owned_documents = relationship("Document", back_populates="owner", foreign_keys="Document.owner_id")
    permissions = relationship(
        "DocumentPermission",
        back_populates="user",
        foreign_keys="[DocumentPermission.user_id]"
    )

    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="user")

    __table_args__ = (
        Index('idx_users_created_at', 'created_at'),
    )


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    current_version_id = Column(UUID(as_uuid=True), ForeignKey("document_versions.id"), nullable=True)
    file_type = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="owned_documents", foreign_keys=[owner_id])
    current_version = relationship("DocumentVersion", foreign_keys=[current_version_id], post_update=True)
    versions = relationship("DocumentVersion", back_populates="document", foreign_keys="DocumentVersion.document_id", cascade="all, delete-orphan")
    tags = relationship("DocumentTag", back_populates="document", cascade="all, delete-orphan")
    permissions = relationship("DocumentPermission", back_populates="document", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="document")

    __table_args__ = (
        Index('idx_documents_owner_id', 'owner_id'),
        Index('idx_documents_created_at', 'created_at'),
        Index('idx_documents_updated_at', 'updated_at'),
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    s3_key = Column(String(1024), nullable=False)
    file_name = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)
    checksum = Column(String(64), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="versions", foreign_keys=[document_id])
    creator = relationship("User")

    __table_args__ = (
        UniqueConstraint('document_id', 'version_number', name='uq_document_version'),
        CheckConstraint('version_number > 0', name='check_positive_version_number'),
        CheckConstraint('file_size > 0', name='check_positive_file_size'),
        Index('idx_document_versions_document_id', 'document_id', 'version_number'),
        Index('idx_document_versions_created_at', 'created_at'),
    )


class DocumentTag(Base):
    __tablename__ = "document_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    tag = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="tags")

    __table_args__ = (
        UniqueConstraint('document_id', 'tag', name='uq_document_tag'),
        Index('idx_document_tags_document_id', 'document_id'),
    )


class DocumentPermission(Base):
    __tablename__ = "document_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(SQLEnum(PermissionRole), nullable=False, default=PermissionRole.READ)
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="permissions")
    user = relationship("User", back_populates="permissions", foreign_keys=[user_id])
    granter = relationship("User", foreign_keys=[granted_by])

    __table_args__ = (
        UniqueConstraint('document_id', 'user_id', name='uq_document_user_permission'),
        Index('idx_document_permissions_document_id', 'document_id'),
        Index('idx_document_permissions_user_id', 'user_id'),
        Index('idx_document_permissions_role', 'role'),
    )


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    details = Column(JSONB, nullable=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="activity_logs")
    document = relationship("Document", back_populates="activity_logs")

    __table_args__ = (
        Index('idx_activity_logs_user_id', 'user_id', 'created_at'),
        Index('idx_activity_logs_document_id', 'document_id', 'created_at'),
        Index('idx_activity_logs_created_at', 'created_at'),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(500), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index('idx_refresh_tokens_user_id', 'user_id'),
    )
