from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint.

    Returns service status and dependency health.
    """
    # Check database connection
    db_healthy = False
    try:
        await db.execute(text("SELECT 1"))
        db_healthy = True
    except Exception:
        pass

    # Check S3 connection (optional - can be expensive)
    s3_healthy = True  # Assume healthy unless we implement a check

    overall_healthy = db_healthy and s3_healthy

    return {
        "status": "healthy" if overall_healthy else "unhealthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "dependencies": {
            "database": "up" if db_healthy else "down",
            "s3": "up" if s3_healthy else "unknown"
        }
    }
