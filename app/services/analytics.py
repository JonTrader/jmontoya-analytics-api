from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from ua_parser import user_agent_parser

from app.models import AnalyticsEvent
from app.schemas import (
    DashboardStats,
    DeviceBreakdown,
    EventsOverTime,
    TopLink,
    TopPage,
    TopProject,
    TrafficSource,
)


def parse_user_agent(user_agent_string: str) -> dict[str, str | None]:
    """Parse a User-Agent string into browser and OS names.

    Returns `None` for either value if the input is empty or cannot be parsed.
    """
    if not user_agent_string:
        return {"browser": None, "os": None}

    parsed = user_agent_parser.Parse(user_agent_string)

    browser_family = parsed.get("user_agent", {}).get("family")
    browser_major = parsed.get("user_agent", {}).get("major")
    browser = " ".join(part for part in [browser_family, browser_major] if part).strip() or None

    os_family = parsed.get("os", {}).get("family")
    os_major = parsed.get("os", {}).get("major")
    os = " ".join(part for part in [os_family, os_major] if part).strip() or None

    return {"browser": browser, "os": os}


async def get_dashboard_stats(db: AsyncSession) -> DashboardStats:
    """Compute aggregate analytics for the public dashboard."""
    # Totals
    total_events_result = await db.execute(select(func.count(AnalyticsEvent.id)))
    total_events = total_events_result.scalar_one()

    unique_sessions_result = await db.execute(
        select(func.count(func.distinct(AnalyticsEvent.session_id)))
    )
    unique_sessions = unique_sessions_result.scalar_one()

    # Events by type
    events_by_type: dict[str, int] = {}
    type_result = await db.execute(
        select(AnalyticsEvent.event_type, func.count(AnalyticsEvent.id).label("count")).group_by(
            AnalyticsEvent.event_type
        )
    )
    for event_type, count in type_result.all():
        events_by_type[event_type] = count

    # Top clicked links (label + href)
    top_links_result = await db.execute(
        select(
            AnalyticsEvent.label,
            AnalyticsEvent.href,
            func.count(AnalyticsEvent.id).label("count"),
        )
        .group_by(AnalyticsEvent.label, AnalyticsEvent.href)
        .order_by(desc("count"))
        .limit(5)
    )
    top_links = [
        TopLink(label=label, href=href, count=count)
        for label, href, count in top_links_result.all()
    ]

    # Most clicked projects by context
    top_projects_result = await db.execute(
        select(AnalyticsEvent.context, func.count(AnalyticsEvent.id).label("count"))
        .where(AnalyticsEvent.context.is_not(None))
        .group_by(AnalyticsEvent.context)
        .order_by(desc("count"))
        .limit(5)
    )
    top_projects = [
        TopProject(context=context, count=count) for context, count in top_projects_result.all()
    ]

    # Device breakdown
    device_result = await db.execute(
        select(AnalyticsEvent.device_type, func.count(AnalyticsEvent.id).label("count"))
        .group_by(AnalyticsEvent.device_type)
        .order_by(desc("count"))
    )
    device_breakdown = [
        DeviceBreakdown(device_type=device_type, count=count)
        for device_type, count in device_result.all()
    ]

    # Top pages
    top_pages_result = await db.execute(
        select(AnalyticsEvent.pathname, func.count(AnalyticsEvent.id).label("count"))
        .group_by(AnalyticsEvent.pathname)
        .order_by(desc("count"))
        .limit(5)
    )
    top_pages = [
        TopPage(pathname=pathname, count=count) for pathname, count in top_pages_result.all()
    ]

    # Traffic sources (referrers)
    referrer_result = await db.execute(
        select(AnalyticsEvent.referrer, func.count(AnalyticsEvent.id).label("count"))
        .where(AnalyticsEvent.referrer.is_not(None))
        .group_by(AnalyticsEvent.referrer)
        .order_by(desc("count"))
        .limit(5)
    )
    traffic_sources = [
        TrafficSource(referrer=referrer, count=count) for referrer, count in referrer_result.all()
    ]

    # Events over the last 30 days
    cutoff = datetime.now(UTC) - timedelta(days=30)
    over_time_result = await db.execute(
        select(
            func.date(AnalyticsEvent.created_at).label("date"),
            func.count(AnalyticsEvent.id).label("count"),
        )
        .where(AnalyticsEvent.created_at >= cutoff)
        .group_by(func.date(AnalyticsEvent.created_at))
        .order_by(func.date(AnalyticsEvent.created_at))
    )
    events_over_time = [
        EventsOverTime(date=date_value, count=count) for date_value, count in over_time_result.all()
    ]

    # Average hover duration
    avg_hover_result = await db.execute(
        select(func.avg(AnalyticsEvent.duration_ms).label("avg_duration"))
        .where(AnalyticsEvent.event_type == "hover")
        .where(AnalyticsEvent.duration_ms.is_not(None))
    )
    avg_hover = avg_hover_result.scalar_one_or_none()
    average_hover_duration = float(avg_hover) if avg_hover is not None else None

    return DashboardStats(
        total_events=total_events,
        unique_sessions=unique_sessions,
        events_by_type=events_by_type,
        top_links=top_links,
        top_projects=top_projects,
        device_breakdown=device_breakdown,
        top_pages=top_pages,
        traffic_sources=traffic_sources,
        events_over_time=events_over_time,
        average_hover_duration=average_hover_duration,
    )
