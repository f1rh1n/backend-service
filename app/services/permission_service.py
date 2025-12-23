from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
from uuid import UUID

from app.models import DocumentPermission, Document, User, PermissionRole
from app.schemas import PermissionCreate, PermissionUpdate
from app.utils.exceptions import PermissionDeniedError


class PermissionService:
    @staticmethod
    async def grant_permission(
        db: AsyncSession,
        document: Document,
        permission_data: PermissionCreate,
        granted_by: User
    ) -> DocumentPermission:
        """Grant permission to a user on a document."""
        # Check if permission already exists
        result = await db.execute(
            select(DocumentPermission).where(
                DocumentPermission.document_id == document.id,
                DocumentPermission.user_id == permission_data.user_id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing permission
            existing.role = permission_data.role
            existing.granted_by = granted_by.id
            await db.commit()
            await db.refresh(existing)
            return existing
        else:
            # Create new permission
            permission = DocumentPermission(
                document_id=document.id,
                user_id=permission_data.user_id,
                role=permission_data.role,
                granted_by=granted_by.id
            )
            db.add(permission)
            await db.commit()
            await db.refresh(permission)
            return permission

    @staticmethod
    async def get_document_permissions(
        db: AsyncSession,
        document_id: UUID
    ) -> List[DocumentPermission]:
        """Get all permissions for a document."""
        result = await db.execute(
            select(DocumentPermission)
            .where(DocumentPermission.document_id == document_id)
            .order_by(DocumentPermission.granted_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_permission(
        db: AsyncSession,
        document_id: UUID,
        user_id: UUID,
        permission_data: PermissionUpdate
    ) -> Optional[DocumentPermission]:
        """Update an existing permission."""
        result = await db.execute(
            select(DocumentPermission).where(
                DocumentPermission.document_id == document_id,
                DocumentPermission.user_id == user_id
            )
        )
        permission = result.scalar_one_or_none()

        if permission:
            permission.role = permission_data.role
            await db.commit()
            await db.refresh(permission)
            return permission

        return None

    @staticmethod
    async def revoke_permission(
        db: AsyncSession,
        document_id: UUID,
        user_id: UUID
    ) -> bool:
        """Revoke a user's permission on a document."""
        result = await db.execute(
            delete(DocumentPermission).where(
                DocumentPermission.document_id == document_id,
                DocumentPermission.user_id == user_id
            )
        )
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def check_permission(
        db: AsyncSession,
        document: Document,
        user: User,
        required_role: PermissionRole = PermissionRole.READ
    ) -> bool:
        """Check if a user has the required permission on a document."""
        # Owner has all permissions
        if document.owner_id == user.id:
            return True

        # Check explicit permissions
        result = await db.execute(
            select(DocumentPermission).where(
                DocumentPermission.document_id == document.id,
                DocumentPermission.user_id == user.id
            )
        )
        permission = result.scalar_one_or_none()

        if not permission:
            return False

        # Role hierarchy: ADMIN > EDIT > READ
        role_hierarchy = {
            PermissionRole.READ: 1,
            PermissionRole.EDIT: 2,
            PermissionRole.ADMIN: 3
        }

        return role_hierarchy[permission.role] >= role_hierarchy[required_role]

    @staticmethod
    async def get_user_accessible_documents(
        db: AsyncSession,
        user_id: UUID,
        min_role: PermissionRole = PermissionRole.READ
    ) -> List[UUID]:
        """Get list of document IDs that a user can access with at least the specified role."""
        role_hierarchy = {
            PermissionRole.READ: 1,
            PermissionRole.EDIT: 2,
            PermissionRole.ADMIN: 3
        }
        min_level = role_hierarchy[min_role]

        # Get documents where user has permission
        result = await db.execute(
            select(DocumentPermission.document_id).where(
                DocumentPermission.user_id == user_id
            )
        )
        permitted_docs = [row[0] for row in result.all()]

        # Add documents owned by user
        result = await db.execute(
            select(Document.id).where(Document.owner_id == user_id)
        )
        owned_docs = [row[0] for row in result.all()]

        # Combine and return unique document IDs
        all_docs = list(set(permitted_docs + owned_docs))
        return all_docs


permission_service = PermissionService()
