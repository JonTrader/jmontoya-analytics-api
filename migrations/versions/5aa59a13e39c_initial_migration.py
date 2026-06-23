"""Initial migration

Revision ID: 5aa59a13e39c
Revises: 
Create Date: 2026-06-20 21:50:48.583152

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5aa59a13e39c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the analytics_events table."""
    op.create_table(
        "analytics_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("context", sa.String(), nullable=True),
        sa.Column("href", sa.String(), nullable=True),
        sa.Column("pathname", sa.String(), nullable=False),
        sa.Column("device_type", sa.String(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("referrer", sa.String(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("browser", sa.String(), nullable=True),
        sa.Column("os", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop the analytics_events table."""
    op.drop_table("analytics_events")
