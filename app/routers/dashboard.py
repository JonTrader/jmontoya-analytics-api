from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import DashboardStats
from app.services.analytics import get_dashboard_stats

router = APIRouter(prefix="/api/analytics", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(db: AsyncSession = Depends(get_db)) -> DashboardStats:
    """Return aggregate analytics data for the public dashboard."""
    return await get_dashboard_stats(db)
