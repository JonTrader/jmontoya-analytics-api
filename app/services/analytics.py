from datetime import UTC, datetime, time, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from ua_parser import user_agent_parser

from app.models import AnalyticsEvent
from app.schemas import (
    BrowserBreakdown,
    BrowserDevice,
    DashboardStats,
    DeviceBreakdown,
    EventsOverTime,
    OsBreakdown,
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


_EXTERNAL = AnalyticsEvent.event_metadata["external"].as_boolean()


async def get_dashboard_stats(db: AsyncSession) -> DashboardStats:
    """Compute aggregate analytics for the public dashboard."""
    total_events = (await db.execute(select(func.count(AnalyticsEvent.id)))).scalar_one()

    unique_sessions = (
        await db.execute(select(func.count(func.distinct(AnalyticsEvent.session_id))))
    ).scalar_one()

    type_result = await db.execute(
        select(AnalyticsEvent.event_type, func.count(AnalyticsEvent.id).label("count")).group_by(
            AnalyticsEvent.event_type
        )
    )
    events_by_type: dict[str, int] = {event_type: count for event_type, count in type_result.all()}

    avg_hover = (
        await db.execute(
            select(func.avg(AnalyticsEvent.duration_ms))
            .where(AnalyticsEvent.event_type == "hover")
            .where(AnalyticsEvent.duration_ms.is_not(None))
        )
    ).scalar_one_or_none()
    average_hover_duration = float(avg_hover) if avg_hover is not None else None

    page_view_count = (
        await db.execute(
            select(func.count(AnalyticsEvent.id)).where(AnalyticsEvent.event_type == "page_view")
        )
    ).scalar_one()
    avg_pages_per_session = round(page_view_count / unique_sessions, 2) if unique_sessions else None

    now = datetime.now(UTC)
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)
    this_week = (
        await db.execute(
            select(func.count(AnalyticsEvent.id)).where(AnalyticsEvent.created_at >= week_ago)
        )
    ).scalar_one()
    prev_week = (
        await db.execute(
            select(func.count(AnalyticsEvent.id))
            .where(AnalyticsEvent.created_at >= two_weeks_ago)
            .where(AnalyticsEvent.created_at < week_ago)
        )
    ).scalar_one()
    wow_event_growth_pct = (
        round(((this_week - prev_week) / prev_week) * 100, 1) if prev_week else None
    )

    ext_result = await db.execute(
        select(_EXTERNAL.label("external"), func.count(AnalyticsEvent.id).label("count"))
        .where(AnalyticsEvent.event_type == "click")
        .group_by(_EXTERNAL)
    )
    internal_clicks = 0
    external_clicks = 0
    for ext_val, count in ext_result.all():
        if ext_val is True:
            external_clicks += count
        else:
            internal_clicks += count
    clicks_by_external = {"internal": internal_clicks, "external": external_clicks}

    today = now.date()
    dates = [today - timedelta(days=i) for i in range(13, -1, -1)]
    cutoff = datetime.combine(dates[0], time(0, 0), tzinfo=UTC)
    date_expr = func.date(AnalyticsEvent.created_at)
    over_time_result = await db.execute(
        select(date_expr.label("d"), AnalyticsEvent.event_type, func.count(AnalyticsEvent.id))
        .where(AnalyticsEvent.created_at >= cutoff)
        .group_by(date_expr, AnalyticsEvent.event_type)
    )
    over_time_counts: dict[tuple[str, str], int] = {}
    for d, event_type, count in over_time_result.all():
        over_time_counts[(d.isoformat(), event_type)] = count
    events_over_time = [
        EventsOverTime(
            date=date.isoformat(),
            page_view=over_time_counts.get((date.isoformat(), "page_view"), 0),
            click=over_time_counts.get((date.isoformat(), "click"), 0),
            hover=over_time_counts.get((date.isoformat(), "hover"), 0),
        )
        for date in dates
    ]

    device_result = await db.execute(
        select(AnalyticsEvent.device_type, func.count(AnalyticsEvent.id).label("count"))
        .group_by(AnalyticsEvent.device_type)
        .order_by(desc("count"))
    )
    device_breakdown = [
        DeviceBreakdown(device=device_type, count=count)
        for device_type, count in device_result.all()
    ]

    browser_result = await db.execute(
        select(AnalyticsEvent.browser, func.count(AnalyticsEvent.id).label("count"))
        .group_by(AnalyticsEvent.browser)
        .order_by(desc("count"))
    )
    browser_breakdown = [
        BrowserBreakdown(browser=browser or "Unknown", count=count)
        for browser, count in browser_result.all()
    ]

    os_result = await db.execute(
        select(AnalyticsEvent.os, func.count(AnalyticsEvent.id).label("count"))
        .group_by(AnalyticsEvent.os)
        .order_by(desc("count"))
    )
    os_breakdown = [
        OsBreakdown(os=os_value or "Unknown", count=count) for os_value, count in os_result.all()
    ]

    bd_result = await db.execute(
        select(
            AnalyticsEvent.browser,
            AnalyticsEvent.device_type,
            func.count(AnalyticsEvent.id).label("count"),
        )
        .group_by(AnalyticsEvent.browser, AnalyticsEvent.device_type)
        .order_by(desc("count"))
    )
    browser_device_matrix = [
        BrowserDevice(browser=browser or "Unknown", device=device_type, count=count)
        for browser, device_type, count in bd_result.all()
    ]

    top_links_result = await db.execute(
        select(
            AnalyticsEvent.label,
            func.count(AnalyticsEvent.id)
            .filter(AnalyticsEvent.event_type == "click")
            .label("clicks"),
            func.count(AnalyticsEvent.id)
            .filter(AnalyticsEvent.event_type == "hover")
            .label("hovers"),
            func.avg(AnalyticsEvent.duration_ms)
            .filter(AnalyticsEvent.event_type == "hover")
            .label("avg_hover"),
            func.sum(AnalyticsEvent.duration_ms)
            .filter(AnalyticsEvent.event_type == "hover")
            .label("total_hover"),
            func.max(AnalyticsEvent.href).label("href"),
            func.bool_or(_EXTERNAL).label("external"),
        )
        .where(AnalyticsEvent.event_type.in_(("click", "hover")))
        .group_by(AnalyticsEvent.label)
        .order_by(desc("clicks"))
        .limit(10)
    )
    top_links = [
        TopLink(
            label=label,
            href=href or "",
            external=bool(external_val),
            clicks=clicks,
            hovers=hovers,
            avg_hover_duration_ms=float(avg_hover) if avg_hover is not None else 0.0,
            total_hover_duration_ms=float(total_hover) if total_hover is not None else 0.0,
        )
        for label, clicks, hovers, avg_hover, total_hover, href, external_val in (
            top_links_result.all()
        )
    ]

    views_result = await db.execute(
        select(AnalyticsEvent.pathname, func.count(AnalyticsEvent.id).label("views"))
        .where(AnalyticsEvent.event_type == "page_view")
        .group_by(AnalyticsEvent.pathname)
        .order_by(desc("views"))
        .limit(10)
    )
    pv_result = await db.execute(
        select(
            AnalyticsEvent.session_id,
            AnalyticsEvent.referrer,
            AnalyticsEvent.pathname,
            AnalyticsEvent.created_at,
        ).where(AnalyticsEvent.event_type == "page_view")
    )
    first_pv: dict[str, str] = {}
    last_pv: dict[str, str] = {}
    first_ts: dict[str, datetime] = {}
    last_ts: dict[str, datetime] = {}
    landing: dict[str | None, str] = {}
    landing_ts: dict[str | None, datetime] = {}
    for session_id, referrer, pathname, created_at in pv_result.all():
        path = pathname or ""
        if session_id not in first_ts or created_at < first_ts[session_id]:
            first_ts[session_id] = created_at
            first_pv[session_id] = path
        if session_id not in last_ts or created_at > last_ts[session_id]:
            last_ts[session_id] = created_at
            last_pv[session_id] = path
        if referrer not in landing_ts or created_at < landing_ts[referrer]:
            landing_ts[referrer] = created_at
            landing[referrer] = path
    entries: dict[str, int] = {}
    for path in first_pv.values():
        entries[path] = entries.get(path, 0) + 1
    exits: dict[str, int] = {}
    for path in last_pv.values():
        exits[path] = exits.get(path, 0) + 1
    top_pages = [
        TopPage(
            pathname=pathname,
            views=views,
            entries=entries.get(pathname, 0),
            exits=exits.get(pathname, 0),
        )
        for pathname, views in views_result.all()
    ]

    projects_result = await db.execute(
        select(
            AnalyticsEvent.context,
            func.count(AnalyticsEvent.id)
            .filter(AnalyticsEvent.event_type == "click")
            .label("clicks"),
            func.count(AnalyticsEvent.id)
            .filter(AnalyticsEvent.event_type == "hover")
            .label("views"),
        )
        .where(AnalyticsEvent.context.is_not(None))
        .group_by(AnalyticsEvent.context)
        .order_by(desc("views"))
        .limit(10)
    )
    top_projects = [
        TopProject(slug=context, title=context, views=views, clicks=clicks)
        for context, clicks, views in projects_result.all()
    ]

    sessions_result = await db.execute(
        select(
            AnalyticsEvent.referrer,
            func.count(func.distinct(AnalyticsEvent.session_id)).label("sessions"),
        )
        .group_by(AnalyticsEvent.referrer)
        .order_by(desc("sessions"))
        .limit(10)
    )
    traffic_sources = [
        TrafficSource(
            referrer=referrer,
            sessions=sessions,
            landing_pathname=landing.get(referrer, ""),
        )
        for referrer, sessions in sessions_result.all()
    ]

    exit_links_result = await db.execute(
        select(
            AnalyticsEvent.label,
            AnalyticsEvent.href,
            func.count(AnalyticsEvent.id)
            .filter(AnalyticsEvent.event_type == "click")
            .label("clicks"),
            func.count(AnalyticsEvent.id)
            .filter(AnalyticsEvent.event_type == "hover")
            .label("hovers"),
            func.avg(AnalyticsEvent.duration_ms)
            .filter(AnalyticsEvent.event_type == "hover")
            .label("avg_hover"),
            func.sum(AnalyticsEvent.duration_ms)
            .filter(AnalyticsEvent.event_type == "hover")
            .label("total_hover"),
        )
        .where(AnalyticsEvent.event_type.in_(("click", "hover")))
        .where(_EXTERNAL.is_(True))
        .group_by(AnalyticsEvent.label, AnalyticsEvent.href)
        .order_by(desc("clicks"))
        .limit(10)
    )
    top_exit_links = [
        TopLink(
            label=label,
            href=href or "",
            external=True,
            clicks=clicks,
            hovers=hovers,
            avg_hover_duration_ms=float(avg_hover) if avg_hover is not None else 0.0,
            total_hover_duration_ms=float(total_hover) if total_hover is not None else 0.0,
        )
        for label, href, clicks, hovers, avg_hover, total_hover in exit_links_result.all()
    ]

    submissions = (
        await db.execute(
            select(func.count(AnalyticsEvent.id)).where(
                AnalyticsEvent.event_type == "contact_submit"
            )
        )
    ).scalar_one()
    contact_views = (
        await db.execute(
            select(func.count(AnalyticsEvent.id))
            .where(AnalyticsEvent.event_type == "page_view")
            .where(AnalyticsEvent.pathname == "/contact")
        )
    ).scalar_one()
    contact_conversion_rate = (
        round((submissions / contact_views) * 100, 1) if contact_views else None
    )

    return DashboardStats(
        total_events=total_events,
        unique_sessions=unique_sessions,
        average_hover_duration=average_hover_duration,
        avg_pages_per_session=avg_pages_per_session,
        wow_event_growth_pct=wow_event_growth_pct,
        clicks_by_external=clicks_by_external,
        events_by_type=events_by_type,
        events_over_time=events_over_time,
        device_breakdown=device_breakdown,
        browser_breakdown=browser_breakdown,
        os_breakdown=os_breakdown,
        browser_device_matrix=browser_device_matrix,
        top_links=top_links,
        top_pages=top_pages,
        top_projects=top_projects,
        traffic_sources=traffic_sources,
        top_exit_links=top_exit_links,
        contact_conversion_rate=contact_conversion_rate,
    )
