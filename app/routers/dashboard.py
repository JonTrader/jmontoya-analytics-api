from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import DashboardStats

router = APIRouter(prefix="/api/analytics", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(db: AsyncSession = Depends(get_db)) -> DashboardStats:
    """
    Return aggregate analytics data for the public dashboard.
    """
    return DashboardStats(
        total_events=0,
        unique_sessions=0,
        events_by_type={},
        top_links=[],
        top_projects=[],
        device_breakdown=[],
        top_pages=[],
        traffic_sources=[],
        events_over_time=[],
        average_hover_duration=None,
    )
