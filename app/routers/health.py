from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Return API health status, including a simple database connectivity check."""
    try:
        await db.execute(text("SELECT 1"))
        database_status = "ok"
    except SQLAlchemyError as e:
        database_status = f"error: {e}"

    return {"status": "ok", "database": database_status}
