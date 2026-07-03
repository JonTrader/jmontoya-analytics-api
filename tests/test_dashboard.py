import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AnalyticsEvent

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _event(**kwargs) -> AnalyticsEvent:
    """Build an AnalyticsEvent with sensible defaults; overrides via kwargs."""
    created_at = kwargs.pop("created_at", None)
    defaults: dict = {
        "event_type": "page_view",
        "label": "page_view",
        "pathname": "/",
        "device_type": "desktop",
        "session_id": "s1",
        "context": None,
        "href": None,
        "duration_ms": None,
        "referrer": None,
        "event_metadata": None,
        "browser": None,
        "os": None,
        "id": uuid4(),
    }
    defaults.update(kwargs)
    if created_at is not None:
        defaults["created_at"] = created_at
    return AnalyticsEvent(**defaults)


async def test_dashboard_empty(client: AsyncClient) -> None:
    response = await client.get("/api/analytics/dashboard")
    assert response.status_code == 200
    data = response.json()

    assert set(data.keys()) == {
        "total_events",
        "unique_sessions",
        "average_hover_duration",
        "avg_pages_per_session",
        "wow_event_growth_pct",
        "clicks_by_external",
        "events_by_type",
        "events_over_time",
        "device_breakdown",
        "browser_breakdown",
        "os_breakdown",
        "browser_device_matrix",
        "top_links",
        "top_pages",
        "top_projects",
        "traffic_sources",
        "top_exit_links",
        "contact_conversion_rate",
    }

    assert data["total_events"] == 0
    assert data["unique_sessions"] == 0
    assert data["average_hover_duration"] is None
    assert data["avg_pages_per_session"] is None
    assert data["wow_event_growth_pct"] is None
    assert data["clicks_by_external"] == {"internal": 0, "external": 0}
    assert data["events_by_type"] == {}
    assert data["device_breakdown"] == []
    assert data["browser_breakdown"] == []
    assert data["os_breakdown"] == []
    assert data["browser_device_matrix"] == []
    assert data["top_links"] == []
    assert data["top_pages"] == []
    assert data["top_projects"] == []
    assert data["traffic_sources"] == []
    assert data["top_exit_links"] == []
    assert data["contact_conversion_rate"] is None

    over_time = data["events_over_time"]
    assert len(over_time) == 14
    assert DATE_RE.match(over_time[0]["date"])
    assert over_time[0] == {
        "date": over_time[0]["date"],
        "page_view": 0,
        "click": 0,
        "hover": 0,
    }
    dates = [row["date"] for row in over_time]
    assert dates == sorted(dates)


async def test_dashboard_with_events(client: AsyncClient, db_session: AsyncSession) -> None:
    db_session.add_all(
        [
            _event(
                event_type="page_view",
                pathname="/projects",
                session_id="s1",
                referrer="google.com",
                device_type="desktop",
                browser="Chrome",
                os="Windows",
            ),
            _event(
                event_type="click",
                label="GitHub",
                href="https://github.com",
                context="MaxApp",
                session_id="s1",
                referrer="google.com",
                device_type="desktop",
                browser="Chrome",
                os="Windows",
                event_metadata={"external": True},
            ),
            _event(
                event_type="hover",
                label="GitHub",
                href="https://github.com",
                context="MaxApp",
                duration_ms=1500,
                session_id="s1",
                referrer="google.com",
                device_type="desktop",
                browser="Chrome",
                os="Windows",
                event_metadata={"external": True},
            ),
            _event(
                event_type="page_view",
                pathname="/contact",
                session_id="s2",
                referrer=None,
                device_type="mobile",
                browser="Safari",
                os="iOS",
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/analytics/dashboard")
    assert response.status_code == 200
    data = response.json()

    assert data["total_events"] == 4
    assert data["unique_sessions"] == 2
    assert data["events_by_type"] == {"page_view": 2, "click": 1, "hover": 1}
    assert data["average_hover_duration"] == 1500.0
    assert data["avg_pages_per_session"] == 1.0
    assert data["wow_event_growth_pct"] is None
    assert data["clicks_by_external"] == {"internal": 0, "external": 1}
    assert data["contact_conversion_rate"] == 0.0

    assert {b["device"]: b["count"] for b in data["device_breakdown"]} == {
        "desktop": 3,
        "mobile": 1,
    }
    assert {b["browser"]: b["count"] for b in data["browser_breakdown"]} == {
        "Chrome": 3,
        "Safari": 1,
    }
    assert {b["os"]: b["count"] for b in data["os_breakdown"]} == {
        "Windows": 3,
        "iOS": 1,
    }
    assert {(b["browser"], b["device"]): b["count"] for b in data["browser_device_matrix"]} == {
        ("Chrome", "desktop"): 3,
        ("Safari", "mobile"): 1,
    }

    assert data["top_links"] == [
        {
            "label": "GitHub",
            "href": "https://github.com",
            "external": True,
            "clicks": 1,
            "hovers": 1,
            "avg_hover_duration_ms": 1500.0,
            "total_hover_duration_ms": 1500.0,
        }
    ]
    assert data["top_exit_links"] == data["top_links"]

    pages = {p["pathname"]: p for p in data["top_pages"]}
    assert pages["/projects"] == {
        "pathname": "/projects",
        "views": 1,
        "entries": 1,
        "exits": 1,
    }
    assert pages["/contact"] == {
        "pathname": "/contact",
        "views": 1,
        "entries": 1,
        "exits": 1,
    }

    assert data["top_projects"] == [{"slug": "MaxApp", "title": "MaxApp", "views": 1, "clicks": 1}]

    sources = {s["referrer"]: s for s in data["traffic_sources"]}
    assert sources["google.com"] == {
        "referrer": "google.com",
        "sessions": 1,
        "landing_pathname": "/projects",
    }
    assert sources[None] == {
        "referrer": None,
        "sessions": 1,
        "landing_pathname": "/contact",
    }

    over_time = data["events_over_time"]
    assert len(over_time) == 14
    today_entry = over_time[-1]
    assert today_entry["page_view"] == 2
    assert today_entry["click"] == 1
    assert today_entry["hover"] == 1


async def test_wow_growth_with_prior_week(client: AsyncClient, db_session: AsyncSession) -> None:
    now = datetime.now(UTC)
    db_session.add_all(
        [
            _event(session_id="a", created_at=now - timedelta(days=10)),
            _event(session_id="b", created_at=now - timedelta(days=3)),
            _event(session_id="c", created_at=now - timedelta(days=1)),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/analytics/dashboard")
    assert response.status_code == 200
    assert response.json()["wow_event_growth_pct"] == 100.0


async def test_wow_growth_null_when_no_prior_week(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    now = datetime.now(UTC)
    db_session.add_all(
        [
            _event(session_id="a", created_at=now - timedelta(days=1)),
            _event(session_id="b", created_at=now - timedelta(days=2)),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/analytics/dashboard")
    assert response.status_code == 200
    assert response.json()["wow_event_growth_pct"] is None


async def test_events_over_time_zero_filled(client: AsyncClient, db_session: AsyncSession) -> None:
    now = datetime.now(UTC)
    db_session.add_all(
        [
            _event(
                event_type="click",
                label="x",
                session_id="a",
                created_at=now - timedelta(days=5),
            ),
            _event(
                event_type="page_view",
                session_id="b",
                created_at=now - timedelta(days=2),
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/analytics/dashboard")
    over_time = response.json()["events_over_time"]
    assert len(over_time) == 14
    dates = [row["date"] for row in over_time]
    assert dates == sorted(dates)

    by_date = {row["date"]: row for row in over_time}
    five_days_ago = (now - timedelta(days=5)).date().isoformat()
    two_days_ago = (now - timedelta(days=2)).date().isoformat()
    assert by_date[five_days_ago]["click"] == 1
    assert by_date[five_days_ago]["page_view"] == 0
    assert by_date[two_days_ago]["page_view"] == 1
    zero_rows = [
        r for r in over_time if r["page_view"] == 0 and r["click"] == 0 and r["hover"] == 0
    ]
    assert len(zero_rows) == 12


async def test_top_pages_entries_and_exits(client: AsyncClient, db_session: AsyncSession) -> None:
    now = datetime.now(UTC)
    db_session.add_all(
        [
            _event(
                event_type="page_view",
                pathname="/a",
                session_id="s1",
                created_at=now - timedelta(seconds=30),
            ),
            _event(
                event_type="page_view",
                pathname="/b",
                session_id="s1",
                created_at=now - timedelta(seconds=20),
            ),
            _event(
                event_type="page_view",
                pathname="/b",
                session_id="s2",
                created_at=now - timedelta(seconds=10),
            ),
            _event(
                event_type="page_view",
                pathname="/a",
                session_id="s3",
                created_at=now - timedelta(seconds=5),
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/analytics/dashboard")
    pages = {p["pathname"]: p for p in response.json()["top_pages"]}
    assert pages["/a"] == {"pathname": "/a", "views": 2, "entries": 2, "exits": 1}
    assert pages["/b"] == {"pathname": "/b", "views": 2, "entries": 1, "exits": 2}


async def test_contact_conversion_rate(client: AsyncClient, db_session: AsyncSession) -> None:
    db_session.add_all(
        [
            _event(
                event_type="contact_submit",
                label="contact_submit",
                pathname="/contact",
                session_id="s1",
            ),
            _event(
                event_type="page_view",
                pathname="/contact",
                session_id="s2",
            ),
            _event(
                event_type="page_view",
                pathname="/contact",
                session_id="s3",
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/analytics/dashboard")
    assert response.json()["contact_conversion_rate"] == 50.0
