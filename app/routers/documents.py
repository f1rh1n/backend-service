from fastapi import APIRouter, Depends, File, UploadFile, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
import math

from app.database import get_db
from app.models import User, Document, PermissionRole
from app.schemas import (
    DocumentCreate, DocumentResponse, DocumentUpdate,
    DocumentSearchParams, PaginatedResponse, UploadResponse,
    DownloadResponse, DocumentVersionResponse, DocumentListResponse,
    PaginationMeta
)
from app.auth import get_current_user
from app.services.document_service import document_service
from app.s3_service import s3_service
from app.utils.dependencies import check_document_permission, validate_file_upload
from app.config import settings

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    title: str = Query(..., description="Document title"),
    description: str | None = Query(None, description="Document description"),
    tags: List[str] = Query(default=[], description="Document tags"),
    file: UploadFile = Depends(validate_file_upload),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a new document.

    - **title**: Document title (required)
    - **description**: Document description (optional)
    - **tags**: List of tags (optional)
    - **file**: File to upload (required)

    Returns document ID, version ID, and upload details.
    """
    document_data = DocumentCreate(title=title, description=description, tags=tags)
    document, version = await document_service.create_document(
        db, document_data, file, current_user
    )

    return UploadResponse(
        document_id=document.id,
        version_id=version.id,
        version_number=version.version_number,
        file_name=version.file_name,
        file_size=version.file_size,
        s3_key=version.s3_key
    )


@router.get("", response_model=PaginatedResponse)
async def list_documents(
    title: str | None = Query(None, description="Filter by title (partial match)"),
    tags: List[str] = Query(default=[], description="Filter by tags"),
    file_type: str | None = Query(None, description="Filter by file type"),
    owner_id: UUID | None = Query(None, description="Filter by owner ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List and search documents with pagination and filtering.

    Filters:
    - **title**: Partial text match on title
    - **tags**: Documents with any of these tags
    - **file_type**: Specific file extension
    - **owner_id**: Documents owned by specific user
    - **page**: Page number (default: 1)
    - **limit**: Items per page (default: 20, max: 100)

    Returns paginated list of documents accessible by the current user.
    """
    search_params = DocumentSearchParams(
        title=title,
        tags=tags if tags else None,
        file_type=file_type,
        owner_id=owner_id,
        page=page,
        limit=limit
    )

    documents, total = await document_service.search_documents(db, search_params, current_user.id)

    # Convert to list response format
    doc_list = []
    for doc in documents:
        doc_dict = {
            "id": doc.id,
            "title": doc.title,
            "description": doc.description,
            "owner_id": doc.owner_id,
            "owner_name": f"{doc.owner.first_name} {doc.owner.last_name}",
            "file_type": doc.file_type,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
            "current_version": doc.current_version.version_number if doc.current_version else 0,
            "file_size": doc.current_version.file_size if doc.current_version else 0,
            "tags": [tag.tag for tag in doc.tags]
        }
        doc_list.append(doc_dict)

    total_pages = math.ceil(total / limit) if total > 0 else 0

    return PaginatedResponse(
        success=True,
        data=doc_list,
        pagination=PaginationMeta(
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document: Document = Depends(check_document_permission),
):
    """
    Get document metadata by ID.

    Returns full document details including current version information.
    Requires READ permission.
    """
    return document


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_data: DocumentUpdate,
    document: Document = Depends(
        lambda doc_id=Path(...), user=Depends(get_current_user), db=Depends(get_db):
            check_document_permission(doc_id, user, PermissionRole.EDIT, db)
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Update document metadata (title, description, tags).

    Requires EDIT permission.
    Does not create a new version - use POST /{document_id}/upload-version for that.
    """
    updated_doc = await document_service.update_document(db, document, document_data)
    return updated_doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document: Document = Depends(
        lambda doc_id=Path(...), user=Depends(get_current_user), db=Depends(get_db):
            check_document_permission(doc_id, user, PermissionRole.ADMIN, db)
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Soft delete a document.

    Requires ADMIN permission.
    Document is marked as deleted but files remain in S3.
    """
    await document_service.delete_document(db, document)
    return None


@router.get("/{document_id}/download", response_model=DownloadResponse)
async def download_document(
    document: Document = Depends(check_document_permission),
):
    """
    Get a presigned URL to download the current version of the document.

    Requires READ permission.
    URL expires after configured time (default: 1 hour).
    """
    if not document.current_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document has no versions"
        )

    url = s3_service.generate_presigned_url(
        document.current_version.s3_key,
        expiration=settings.PRESIGNED_URL_EXPIRY
    )

    if not url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL"
        )

    return DownloadResponse(
        url=url,
        expires_in=settings.PRESIGNED_URL_EXPIRY
    )


@router.get("/{document_id}/versions", response_model=List[DocumentVersionResponse])
async def get_document_versions(
    document_id: UUID = Path(...),
    document: Document = Depends(check_document_permission),
    db: AsyncSession = Depends(get_db)
):
    """
    Get version history for a document.

    Requires READ permission.
    Returns all versions ordered by version number (newest first).
    """
    versions = await document_service.get_document_versions(db, document_id)
    return versions


@router.post("/{document_id}/upload-version", response_model=UploadResponse)
async def upload_new_version(
    document_id: UUID = Path(...),
    file: UploadFile = Depends(validate_file_upload),
    document: Document = Depends(
        lambda doc_id=Path(...), user=Depends(get_current_user), db=Depends(get_db):
            check_document_permission(doc_id, user, PermissionRole.EDIT, db)
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a new version of an existing document.

    Requires EDIT permission.
    Creates immutable new version and updates document's current version.
    """
    version = await document_service.create_new_version(db, document, file, current_user)

    return UploadResponse(
        document_id=document.id,
        version_id=version.id,
        version_number=version.version_number,
        file_name=version.file_name,
        file_size=version.file_size,
        s3_key=version.s3_key
    )


@router.get("/{document_id}/versions/{version_id}/download", response_model=DownloadResponse)
async def download_document_version(
    document_id: UUID = Path(...),
    version_id: UUID = Path(...),
    document: Document = Depends(check_document_permission),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a presigned URL to download a specific version of the document.

    Requires READ permission.
    URL expires after configured time (default: 1 hour).
    """
    from sqlalchemy import select
    from app.models import DocumentVersion

    result = await db.execute(
        select(DocumentVersion).where(
            DocumentVersion.id == version_id,
            DocumentVersion.document_id == document_id
        )
    )
    version = result.scalar_one_or_none()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    url = s3_service.generate_presigned_url(
        version.s3_key,
        expiration=settings.PRESIGNED_URL_EXPIRY
    )

    if not url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL"
        )

    return DownloadResponse(
        url=url,
        expires_in=settings.PRESIGNED_URL_EXPIRY
    )


# Import HTTPException
from fastapi import HTTPException
