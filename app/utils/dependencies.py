from fastapi import Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from typing import List
from uuid import UUID

from app.database import get_db
from app.auth import get_current_user
from app.models import User, Document, PermissionRole
from app.utils.exceptions import DocumentNotFoundError, PermissionDeniedError
from app.config import settings
from app.utils.exceptions import InvalidFileTypeError, FileTooLargeError
from sqlalchemy import select


async def get_document_or_404(
    document_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Document:
    """Get a document by ID or raise 404."""
    result = await db.execute(
        select(Document)
        .where(
            Document.id == document_id,
            Document.is_deleted == False  # noqa: E712
        )
        .options(
            joinedload(Document.owner),
            joinedload(Document.current_version),
            joinedload(Document.tags)
        )
    )
    document = result.unique().scalar_one_or_none()

    if not document:
        raise DocumentNotFoundError(str(document_id))

    return document


async def check_document_permission(
    document: Document = Depends(get_document_or_404),
    current_user: User = Depends(get_current_user),
    required_role: PermissionRole = PermissionRole.READ,
    db: AsyncSession = Depends(get_db)
) -> Document:
    """Check if user has required permission on document."""
    # Owner has all permissions
    if document.owner_id == current_user.id:
        return document

    # Check explicit permissions
    from app.models import DocumentPermission
    result = await db.execute(
        select(DocumentPermission).where(
            DocumentPermission.document_id == document.id,
            DocumentPermission.user_id == current_user.id
        )
    )
    permission = result.scalar_one_or_none()

    if not permission:
        raise PermissionDeniedError("You don't have access to this document")

    # Check role hierarchy: ADMIN > EDIT > READ
    role_hierarchy = {
        PermissionRole.READ: 1,
        PermissionRole.EDIT: 2,
        PermissionRole.ADMIN: 3
    }

    if role_hierarchy[permission.role] < role_hierarchy[required_role]:
        raise PermissionDeniedError(f"You need {required_role.value} permission for this action")

    return document


def validate_file_upload(file: UploadFile = File(...)) -> UploadFile:
    """Validate uploaded file."""
    # Check file extension
    filename = file.filename or ""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension not in settings.allowed_extensions_list:
        raise InvalidFileTypeError(extension)

    return file
