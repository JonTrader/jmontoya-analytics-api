from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EventCreate(BaseModel):
    """Request schema for ingesting a new analytics event."""

    event_type: str
    label: str
    context: str | None = None
    href: str | None = None
    pathname: str
    device_type: str
    duration_ms: int | None = None
    session_id: str
    referrer: str | None = None
    metadata: dict | None = None


class EventRead(BaseModel):
    """Response schema returned after storing an event.

    The database column is stored under the attribute `event_metadata` because
    `metadata` is reserved by SQLAlchemy, but the API still exposes it as
    `metadata` to callers.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    label: str
    context: str | None
    href: str | None
    pathname: str
    device_type: str
    duration_ms: int | None
    session_id: str
    referrer: str | None
    metadata: dict | None = Field(
        alias="event_metadata",
        serialization_alias="metadata",
    )
    browser: str | None
    os: str | None
    created_at: datetime


# ------------------------------------------------------------------------------------------------
# Dashboard response models.
#
# Field names are snake_case and must match the Next.js frontend's `DashboardStats` type
# character-for-character (lib/analytics-dashboard.ts). Pydantic v2 emits raw field names
# by default (no alias generator), so no camelCase config is applied here.
# ------------------------------------------------------------------------------------------------


class TopLink(BaseModel):
    label: str
    href: str
    external: bool
    clicks: int
    hovers: int
    avg_hover_duration_ms: float
    total_hover_duration_ms: float


class TopProject(BaseModel):
    slug: str
    title: str
    views: int
    clicks: int


class TopPage(BaseModel):
    pathname: str
    views: int
    entries: int
    exits: int


class TrafficSource(BaseModel):
    referrer: str | None
    sessions: int
    landing_pathname: str


class EventsOverTime(BaseModel):
    date: str
    page_view: int
    click: int
    hover: int


class DeviceBreakdown(BaseModel):
    device: str
    count: int


class BrowserBreakdown(BaseModel):
    browser: str
    count: int


class OsBreakdown(BaseModel):
    os: str
    count: int


class BrowserDevice(BaseModel):
    browser: str
    device: str
    count: int


class DashboardStats(BaseModel):
    """Aggregate statistics returned by the dashboard endpoint."""

    total_events: int
    unique_sessions: int
    average_hover_duration: float | None
    avg_pages_per_session: float | None
    wow_event_growth_pct: float | None
    clicks_by_external: dict[str, int]
    events_by_type: dict[str, int]
    events_over_time: list[EventsOverTime]
    device_breakdown: list[DeviceBreakdown]
    browser_breakdown: list[BrowserBreakdown]
    os_breakdown: list[OsBreakdown]
    browser_device_matrix: list[BrowserDevice]
    top_links: list[TopLink]
    top_pages: list[TopPage]
    top_projects: list[TopProject]
    traffic_sources: list[TrafficSource]
    top_exit_links: list[TopLink]
    contact_conversion_rate: float | None
