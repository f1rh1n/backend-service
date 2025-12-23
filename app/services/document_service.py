from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import joinedload
from typing import List, Optional, Tuple
from uuid import UUID
from fastapi import UploadFile
import mimetypes

from app.models import Document, DocumentVersion, DocumentTag, User, PermissionRole
from app.schemas import DocumentCreate, DocumentUpdate, DocumentSearchParams
from app.s3_service import s3_service
from app.utils.exceptions import FileTooLargeError
from app.config import settings


class DocumentService:
    @staticmethod
    async def create_document(
        db: AsyncSession,
        document_data: DocumentCreate,
        file: UploadFile,
        current_user: User
    ) -> Tuple[Document, DocumentVersion]:
        """Create a new document with its first version."""
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Validate file size
        if file_size > settings.MAX_UPLOAD_SIZE:
            raise FileTooLargeError(file_size, settings.MAX_UPLOAD_SIZE)

        # Determine file type and mime type
        filename = file.filename or "unknown"
        file_extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        mime_type = file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"

        # Create document record
        document = Document(
            title=document_data.title,
            description=document_data.description,
            owner_id=current_user.id,
            file_type=file_extension
        )
        db.add(document)
        await db.flush()  # Get document ID

        # Generate S3 key and upload
        s3_key = s3_service.generate_s3_key(document.id, 1, filename)
        upload_result = await s3_service.upload_file(file_content, s3_key, mime_type)

        if not upload_result.get('success'):
            raise Exception(f"Failed to upload file to S3: {upload_result.get('error')}")

        # Create first version
        version = DocumentVersion(
            document_id=document.id,
            version_number=1,
            s3_key=s3_key,
            file_name=filename,
            file_size=file_size,
            mime_type=mime_type,
            checksum=upload_result.get('checksum'),
            created_by=current_user.id
        )
        db.add(version)
        await db.flush()

        # Set current version
        document.current_version_id = version.id

        # Add tags
        if document_data.tags:
            for tag_name in document_data.tags:
                tag = DocumentTag(document_id=document.id, tag=tag_name.lower().strip())
                db.add(tag)

        await db.commit()
        await db.refresh(document)
        await db.refresh(version)

        return document, version

    @staticmethod
    async def get_document_by_id(db: AsyncSession, document_id: UUID) -> Optional[Document]:
        """Get a document by ID."""
        result = await db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.is_deleted == False  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def search_documents(
        db: AsyncSession,
        params: DocumentSearchParams,
        user_id: UUID
    ) -> Tuple[List[Document], int]:
        """Search and filter documents with pagination."""
        # Base query - documents user owns or has permission to access
        query = select(Document).where(Document.is_deleted == False)  # noqa: E712

        # Filter by accessible documents (owner or has permission)
        from app.models import DocumentPermission
        accessible_subquery = select(DocumentPermission.document_id).where(
            DocumentPermission.user_id == user_id
        )

        query = query.where(
            or_(
                Document.owner_id == user_id,
                Document.id.in_(accessible_subquery)
            )
        )

        # Apply filters
        if params.title:
            query = query.where(Document.title.ilike(f"%{params.title}%"))

        if params.file_type:
            query = query.where(Document.file_type == params.file_type)

        if params.owner_id:
            query = query.where(Document.owner_id == params.owner_id)

        if params.from_date:
            query = query.where(Document.created_at >= params.from_date)

        if params.to_date:
            query = query.where(Document.created_at <= params.to_date)

        if params.tags:
            # Documents that have ANY of the specified tags
            tag_subquery = select(DocumentTag.document_id).where(
                DocumentTag.tag.in_([t.lower() for t in params.tags])
            )
            query = query.where(Document.id.in_(tag_subquery))

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        offset = (params.page - 1) * params.limit
        query = query.order_by(Document.updated_at.desc()).offset(offset).limit(params.limit)

        # Eagerly load relationships to avoid greenlet errors
        query = query.options(
            joinedload(Document.owner),
            joinedload(Document.current_version),
            joinedload(Document.tags)
        )

        # Execute
        result = await db.execute(query)
        documents = result.unique().scalars().all()

        return list(documents), total

    @staticmethod
    async def update_document(
        db: AsyncSession,
        document: Document,
        document_data: DocumentUpdate
    ) -> Document:
        """Update document metadata."""
        if document_data.title is not None:
            document.title = document_data.title

        if document_data.description is not None:
            document.description = document_data.description

        if document_data.tags is not None:
            # Remove existing tags
            await db.execute(
                select(DocumentTag).where(DocumentTag.document_id == document.id)
            )
            result = await db.execute(
                select(DocumentTag).where(DocumentTag.document_id == document.id)
            )
            existing_tags = result.scalars().all()
            for tag in existing_tags:
                await db.delete(tag)

            # Add new tags
            for tag_name in document_data.tags:
                tag = DocumentTag(document_id=document.id, tag=tag_name.lower().strip())
                db.add(tag)

        await db.commit()
        await db.refresh(document)
        return document

    @staticmethod
    async def delete_document(db: AsyncSession, document: Document) -> bool:
        """Soft delete a document."""
        from datetime import datetime
        document.is_deleted = True
        document.deleted_at = datetime.utcnow()
        await db.commit()
        return True

    @staticmethod
    async def get_document_versions(
        db: AsyncSession,
        document_id: UUID
    ) -> List[DocumentVersion]:
        """Get all versions of a document."""
        result = await db.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_new_version(
        db: AsyncSession,
        document: Document,
        file: UploadFile,
        current_user: User
    ) -> DocumentVersion:
        """Create a new version of an existing document."""
        # Get next version number
        result = await db.execute(
            select(func.max(DocumentVersion.version_number))
            .where(DocumentVersion.document_id == document.id)
        )
        max_version = result.scalar() or 0
        next_version = max_version + 1

        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Validate file size
        if file_size > settings.MAX_UPLOAD_SIZE:
            raise FileTooLargeError(file_size, settings.MAX_UPLOAD_SIZE)

        # Determine mime type
        filename = file.filename or "unknown"
        mime_type = file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"

        # Generate S3 key and upload
        s3_key = s3_service.generate_s3_key(document.id, next_version, filename)
        upload_result = await s3_service.upload_file(file_content, s3_key, mime_type)

        if not upload_result.get('success'):
            raise Exception(f"Failed to upload file to S3: {upload_result.get('error')}")

        # Create new version
        version = DocumentVersion(
            document_id=document.id,
            version_number=next_version,
            s3_key=s3_key,
            file_name=filename,
            file_size=file_size,
            mime_type=mime_type,
            checksum=upload_result.get('checksum'),
            created_by=current_user.id
        )
        db.add(version)
        await db.flush()

        # Update document's current version
        document.current_version_id = version.id

        await db.commit()
        await db.refresh(version)

        return version


document_service = DocumentService()
