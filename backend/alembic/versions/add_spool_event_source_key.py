"""add persistent source event key for idempotent consumption

Revision ID: add_spool_event_source_key
Revises: remove_ams_fields
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_spool_event_source_key"
down_revision: Union[str, Sequence[str], None] = "remove_ams_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "spool_events",
        sa.Column("source_event_key", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_spool_events_source_event_key",
        "spool_events",
        ["source_event_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_spool_events_source_event_key", table_name="spool_events")
    op.drop_column("spool_events", "source_event_key")

