from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AnalyticsEvent(Base):
    """A single analytics event ingested from the frontend."""

    __tablename__ = "analytics_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Frontend-provided fields
    event_type: Mapped[str]
    label: Mapped[str]
    context: Mapped[str | None]
    href: Mapped[str | None]
    pathname: Mapped[str]
    device_type: Mapped[str]
    duration_ms: Mapped[int | None]
    session_id: Mapped[str]
    referrer: Mapped[str | None]
    event_metadata: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )

    # Backend-enriched fields
    browser: Mapped[str | None]
    os: Mapped[str | None]

    # Server-generated timestamp
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
    )
