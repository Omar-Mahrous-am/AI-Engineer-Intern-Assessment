"""Initial schema: create weather_records table

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-16 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "weather_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("location_name", sa.String(length=255), nullable=False, comment="Resolved location name"),
        sa.Column("country", sa.String(length=100), nullable=True, comment="Country of the resolved location"),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False, comment="Requested start date"),
        sa.Column("end_date", sa.Date(), nullable=False, comment="Requested end date"),
        sa.Column(
            "weather_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Normalised weather response from provider",
        ),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_weather_records_id", "weather_records", ["id"], unique=False)
    op.create_index(
        "ix_weather_records_location_name",
        "weather_records",
        ["location_name"],
        unique=False,
    )
    op.create_index(
        "ix_weather_records_start_date",
        "weather_records",
        ["start_date"],
        unique=False,
    )
    op.create_index(
        "ix_weather_records_end_date",
        "weather_records",
        ["end_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_weather_records_end_date", table_name="weather_records")
    op.drop_index("ix_weather_records_start_date", table_name="weather_records")
    op.drop_index("ix_weather_records_location_name", table_name="weather_records")
    op.drop_index("ix_weather_records_id", table_name="weather_records")
    op.drop_table("weather_records")
