from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EventCreate(BaseModel):
    """Request schema for ingesting a new analytics event."""

    event_type: str
    label: str
    context: Optional[str] = None
    href: Optional[str] = None
    pathname: str
    device_type: str
    duration_ms: Optional[int] = None
    session_id: str
    referrer: Optional[str] = None
    metadata: Optional[dict] = None


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
    context: Optional[str]
    href: Optional[str]
    pathname: str
    device_type: str
    duration_ms: Optional[int]
    session_id: str
    referrer: Optional[str]
    metadata: Optional[dict] = Field(
        alias="event_metadata",
        serialization_alias="metadata",
    )
    browser: Optional[str]
    os: Optional[str]
    created_at: datetime


class TopLink(BaseModel):
    label: str
    href: Optional[str]
    count: int


class TopProject(BaseModel):
    context: str
    count: int


class DeviceBreakdown(BaseModel):
    device_type: str
    count: int


class TopPage(BaseModel):
    pathname: str
    count: int


class TrafficSource(BaseModel):
    referrer: Optional[str]
    count: int


class EventsOverTime(BaseModel):
    date: date
    count: int


class DashboardStats(BaseModel):
    """Aggregate statistics returned by the dashboard endpoint."""

    total_events: int
    unique_sessions: int
    events_by_type: dict[str, int]
    top_links: list[TopLink]
    top_projects: list[TopProject]
    device_breakdown: list[DeviceBreakdown]
    top_pages: list[TopPage]
    traffic_sources: list[TrafficSource]
    events_over_time: list[EventsOverTime]
    average_hover_duration: Optional[float]
