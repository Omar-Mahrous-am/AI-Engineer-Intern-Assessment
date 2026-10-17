"""src/models/weather_record.py — SQLAlchemy WeatherRecord model."""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import JSON, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.helpers.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class WeatherRecord(Base):
    """Persisted weather request with its results."""

    __tablename__ = "weather_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    location_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Resolved location name"
    )
    country: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Country of the resolved location"
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    start_date: Mapped[date] = mapped_column(nullable=False, comment="Requested start date")
    end_date: Mapped[date] = mapped_column(nullable=False, comment="Requested end date")

    weather_data: Mapped[dict] = mapped_column(
        JSON, nullable=False, comment="Normalised weather response from provider"
    )

    provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default="open-meteo"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    __table_args__ = (
        Index("ix_weather_records_location_name", "location_name"),
        Index("ix_weather_records_start_date", "start_date"),
        Index("ix_weather_records_end_date", "end_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<WeatherRecord id={self.id} location={self.location_name!r} "
            f"start={self.start_date} end={self.end_date}>"
        )
