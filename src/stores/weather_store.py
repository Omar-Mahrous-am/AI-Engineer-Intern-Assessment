"""src/stores/weather_store.py — Database query and persistence operations for WeatherRecord."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.helpers.exceptions import WeatherRecordNotFoundError
from src.helpers.logging import get_logger
from src.models.weather_record import WeatherRecord

logger = get_logger(__name__)


class WeatherStore:
    """All database operations for weather records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        location_name: str,
        country: str | None,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        weather_data: dict[str, Any],
        provider: str = "open-meteo",
    ) -> WeatherRecord:
        record = WeatherRecord(
            location_name=location_name,
            country=country,
            latitude=latitude,
            longitude=longitude,
            start_date=start_date,
            end_date=end_date,
            weather_data=weather_data,
            provider=provider,
        )
        self._session.add(record)
        await self._session.flush()
        await self._session.refresh(record)
        logger.info("Created WeatherRecord id=%d for %r", record.id, location_name)
        return record

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_by_id(self, record_id: int) -> WeatherRecord:
        stmt = select(WeatherRecord).where(WeatherRecord.id == record_id)
        result = await self._session.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            raise WeatherRecordNotFoundError(record_id)
        return record

    async def list_records(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        location: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[WeatherRecord], int]:
        """Return (records, total_count) with optional filters."""
        stmt = select(WeatherRecord)
        count_stmt = select(func.count()).select_from(WeatherRecord)

        if location:
            pattern = f"%{location}%"
            stmt = stmt.where(WeatherRecord.location_name.ilike(pattern))
            count_stmt = count_stmt.where(WeatherRecord.location_name.ilike(pattern))

        if start_date:
            stmt = stmt.where(WeatherRecord.start_date >= start_date)
            count_stmt = count_stmt.where(WeatherRecord.start_date >= start_date)

        if end_date:
            stmt = stmt.where(WeatherRecord.end_date <= end_date)
            count_stmt = count_stmt.where(WeatherRecord.end_date <= end_date)

        total_result = await self._session.execute(count_stmt)
        total: int = total_result.scalar_one()

        stmt = stmt.order_by(WeatherRecord.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        records = list(result.scalars().all())

        return records, total

    async def list_all_for_export(
        self,
        *,
        location: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[WeatherRecord]:
        """Return all matching records for export (no pagination limit)."""
        stmt = select(WeatherRecord)

        if location:
            stmt = stmt.where(WeatherRecord.location_name.ilike(f"%{location}%"))
        if start_date:
            stmt = stmt.where(WeatherRecord.start_date >= start_date)
        if end_date:
            stmt = stmt.where(WeatherRecord.end_date <= end_date)

        stmt = stmt.order_by(WeatherRecord.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update(
        self,
        record_id: int,
        *,
        location_name: str | None = None,
        country: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        weather_data: dict[str, Any] | None = None,
    ) -> WeatherRecord:
        record = await self.get_by_id(record_id)

        if location_name is not None:
            record.location_name = location_name
        if country is not None:
            record.country = country
        if latitude is not None:
            record.latitude = latitude
        if longitude is not None:
            record.longitude = longitude
        if start_date is not None:
            record.start_date = start_date
        if end_date is not None:
            record.end_date = end_date
        if weather_data is not None:
            record.weather_data = weather_data

        record.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._session.refresh(record)
        logger.info("Updated WeatherRecord id=%d", record_id)
        return record

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete(self, record_id: int) -> None:
        record = await self.get_by_id(record_id)
        await self._session.delete(record)
        await self._session.flush()
        logger.info("Deleted WeatherRecord id=%d", record_id)
