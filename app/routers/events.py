from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import verify_api_key
from app.models import AnalyticsEvent
from app.schemas import EventCreate, EventRead
from app.services.analytics import parse_user_agent

router = APIRouter(
    prefix="/api/analytics",
    tags=["events"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/events", response_model=EventRead, status_code=201)
async def create_event(
    event: EventCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AnalyticsEvent:
    """Ingest a new analytics event from the frontend."""
    ua_data = parse_user_agent(request.headers.get("user-agent", ""))

    db_event = AnalyticsEvent(
        event_type=event.event_type,
        label=event.label,
        context=event.context,
        href=event.href,
        pathname=event.pathname,
        device_type=event.device_type,
        duration_ms=event.duration_ms,
        session_id=event.session_id,
        referrer=event.referrer,
        event_metadata=event.metadata,
        browser=ua_data["browser"],
        os=ua_data["os"],
    )

    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)

    return db_event
