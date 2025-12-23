from fastapi import APIRouter, Depends, Path, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.database import get_db
from app.models import User, Document, PermissionRole
from app.schemas import PermissionCreate, PermissionUpdate, PermissionResponse
from app.auth import get_current_user
from app.services.permission_service import permission_service
from app.utils.dependencies import check_document_permission

router = APIRouter(prefix="/documents/{document_id}/permissions", tags=["Permissions"])


@router.post("", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def share_document(
    document_id: UUID = Path(...),
    permission_data: PermissionCreate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Share a document with another user by granting permissions.

    Requires ADMIN permission on the document.

    - **user_id**: ID of the user to grant access to
    - **role**: Permission level (READ, EDIT, or ADMIN)

    If permission already exists, it will be updated.
    """
    # Get the document and check permissions
    from app.utils.dependencies import get_document_or_404
    document = await get_document_or_404(document_id, db)

    # Check ADMIN permission
    if document.owner_id != current_user.id:
        from app.models import DocumentPermission
        from sqlalchemy import select
        result = await db.execute(
            select(DocumentPermission).where(
                DocumentPermission.document_id == document_id,
                DocumentPermission.user_id == current_user.id,
                DocumentPermission.role == PermissionRole.ADMIN
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You need ADMIN permission for this action"
            )

    # Check that user is not sharing with themselves
    if permission_data.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot grant permission to yourself"
        )

    # Verify target user exists
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == permission_data.user_id))
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {permission_data.user_id} not found"
        )

    permission = await permission_service.grant_permission(
        db, document, permission_data, current_user
    )

    return permission


@router.get("", response_model=List[PermissionResponse])
async def list_document_permissions(
    document_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all permissions for a document.

    Requires READ permission on the document.
    Returns list of users with access and their permission levels.
    """
    # Verify user has at least READ access
    from app.utils.dependencies import get_document_or_404
    document = await get_document_or_404(document_id, db)

    if document.owner_id != current_user.id:
        from app.models import DocumentPermission
        from sqlalchemy import select
        result = await db.execute(
            select(DocumentPermission).where(
                DocumentPermission.document_id == document_id,
                DocumentPermission.user_id == current_user.id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this document"
            )

    permissions = await permission_service.get_document_permissions(db, document_id)
    return permissions


@router.put("/{user_id}", response_model=PermissionResponse)
async def update_document_permission(
    document_id: UUID = Path(...),
    user_id: UUID = Path(...),
    permission_data: PermissionUpdate = ...,
    document: Document = Depends(
        lambda doc_id=Path(...), user=Depends(get_current_user), db=Depends(get_db):
            check_document_permission(doc_id, user, PermissionRole.ADMIN, db)
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing permission.

    Requires ADMIN permission on the document.

    - **user_id**: ID of the user whose permission to update
    - **role**: New permission level (READ, EDIT, or ADMIN)
    """
    permission = await permission_service.update_permission(
        db, document_id, user_id, permission_data
    )

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    return permission


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_document_permission(
    document_id: UUID = Path(...),
    user_id: UUID = Path(...),
    document: Document = Depends(
        lambda doc_id=Path(...), user=Depends(get_current_user), db=Depends(get_db):
            check_document_permission(doc_id, user, PermissionRole.ADMIN, db)
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Revoke a user's permission on a document.

    Requires ADMIN permission on the document.

    - **user_id**: ID of the user whose access to revoke

    Note: Cannot revoke permissions from the document owner.
    """
    # Prevent revoking owner's access
    if user_id == document.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke owner's access"
        )

    success = await permission_service.revoke_permission(db, document_id, user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    return None
