"""src/controllers/weather_controller.py — Business logic coordinating stores and weather client."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.helpers import weather_client
from src.helpers.exceptions import InvalidCoordinatesError, InvalidDateRangeError
from src.helpers.logging import get_logger
from src.helpers.weather_normalizer import normalize_current, normalize_forecast
from src.models.weather_record import WeatherRecord
from src.schemas.weather import WeatherSearchRequest, WeatherUpdateRequest
from src.stores.weather_store import WeatherStore

logger = get_logger(__name__)

# Maximum allowed date-range span (days) to protect against abuse
MAX_DATE_RANGE_DAYS = 365


def _validate_date_range(start: date, end: date) -> None:
    if start > end:
        raise InvalidDateRangeError("'start_date' must be on or before 'end_date'.")
    span = (end - start).days
    if span > MAX_DATE_RANGE_DAYS:
        raise InvalidDateRangeError(
            f"Date range may not exceed {MAX_DATE_RANGE_DAYS} days. "
            f"Requested range is {span} days."
        )


class WeatherController:
    def __init__(self, session: AsyncSession) -> None:
        self._store = WeatherStore(session)
        self._session = session

    # ------------------------------------------------------------------
    # Search and persist
    # ------------------------------------------------------------------

    async def search_and_save(self, req: WeatherSearchRequest) -> WeatherRecord:
        _validate_date_range(req.start_date, req.end_date)

        # Resolve location
        if req.location:
            geo = await weather_client.geocode_location(req.location)
            location_name: str = geo.get("name", req.location)
            country: str | None = geo.get("country")
            latitude: float = float(geo["latitude"])
            longitude: float = float(geo["longitude"])
        else:
            # Direct coordinates validated by Pydantic
            latitude = float(req.latitude)  # type: ignore[arg-type]
            longitude = float(req.longitude)  # type: ignore[arg-type]
            location_name = f"{latitude:.4f},{longitude:.4f}"
            country = None

        # Fetch weather BEFORE opening the DB transaction
        weather_data = await weather_client.fetch_weather_for_range(
            latitude, longitude, req.start_date, req.end_date
        )

        # Persist inside a transaction
        record = await self._store.create(
            location_name=location_name,
            country=country,
            latitude=latitude,
            longitude=longitude,
            start_date=req.start_date,
            end_date=req.end_date,
            weather_data=weather_data,
        )
        await self._session.commit()
        await self._session.refresh(record)
        return record

    # ------------------------------------------------------------------
    # Current weather (not persisted)
    # ------------------------------------------------------------------

    async def get_current_weather(
        self,
        location: str | None,
        latitude: float | None,
        longitude: float | None,
    ) -> dict[str, Any]:
        if location:
            geo = await weather_client.geocode_location(location)
            lat: float = float(geo["latitude"])
            lon: float = float(geo["longitude"])
            loc_name: str = geo.get("name", location)
            country: str | None = geo.get("country")
        elif latitude is not None and longitude is not None:
            lat, lon = latitude, longitude
            loc_name = f"{lat:.4f},{lon:.4f}"
            country = None
        else:
            raise InvalidCoordinatesError(
                "Provide either 'location' or both 'latitude' and 'longitude'."
            )

        weather = await weather_client.fetch_current_weather(lat, lon)
        return {
            "location_name": loc_name,
            "country": country,
            "latitude": lat,
            "longitude": lon,
            **normalize_current(weather),  # flat fields for the UI
            "weather": weather,  # original payload kept for compatibility
        }

    # ------------------------------------------------------------------
    # Forecast (not persisted)
    # ------------------------------------------------------------------

    async def get_forecast(
        self,
        location: str | None,
        latitude: float | None,
        longitude: float | None,
        days: int,
    ) -> dict[str, Any]:
        if not (1 <= days <= 16):
            raise InvalidDateRangeError("'days' must be between 1 and 16.")

        if location:
            geo = await weather_client.geocode_location(location)
            lat = float(geo["latitude"])
            lon = float(geo["longitude"])
            loc_name = geo.get("name", location)
            country: str | None = geo.get("country")
        elif latitude is not None and longitude is not None:
            lat, lon = latitude, longitude
            loc_name = f"{lat:.4f},{lon:.4f}"
            country = None
        else:
            raise InvalidCoordinatesError(
                "Provide either 'location' or both 'latitude' and 'longitude'."
            )

        forecast = await weather_client.fetch_forecast(lat, lon, days)
        return {
            "location_name": loc_name,
            "country": country,
            "latitude": lat,
            "longitude": lon,
            "days_requested": days,
            "days": normalize_forecast(forecast),  # list the UI reads
            "forecast": forecast,  # original payload kept for compatibility
        }

    # ------------------------------------------------------------------
    # CRUD on persisted records
    # ------------------------------------------------------------------

    async def list_history(
        self,
        limit: int,
        offset: int,
        location: str | None,
        start_date: date | None,
        end_date: date | None,
    ) -> tuple[list[WeatherRecord], int]:
        return await self._store.list_records(
            limit=limit,
            offset=offset,
            location=location,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_record(self, record_id: int) -> WeatherRecord:
        return await self._store.get_by_id(record_id)

    async def update_record(
        self, record_id: int, req: WeatherUpdateRequest
    ) -> WeatherRecord:
        # Fetch the existing record to compute new state
        existing = await self._store.get_by_id(record_id)

        new_location = req.location
        new_lat = req.latitude
        new_lon = req.longitude
        new_start = req.start_date or existing.start_date
        new_end = req.end_date or existing.end_date

        _validate_date_range(new_start, new_end)

        # Resolve new location / coordinates
        country: str | None = existing.country
        if new_location:
            geo = await weather_client.geocode_location(new_location)
            new_location = geo.get("name", new_location)
            country = geo.get("country")
            new_lat = float(geo["latitude"])
            new_lon = float(geo["longitude"])
        elif new_lat is not None and new_lon is not None:
            new_location = f"{new_lat:.4f},{new_lon:.4f}"
            country = None

        final_lat = new_lat if new_lat is not None else existing.latitude
        final_lon = new_lon if new_lon is not None else existing.longitude
        final_location = new_location if new_location else existing.location_name

        # Re-fetch weather if location or dates changed
        location_changed = final_lat != existing.latitude or final_lon != existing.longitude
        dates_changed = new_start != existing.start_date or new_end != existing.end_date

        new_weather_data = existing.weather_data
        if location_changed or dates_changed:
            new_weather_data = await weather_client.fetch_weather_for_range(
                final_lat, final_lon, new_start, new_end
            )

        record = await self._store.update(
            record_id,
            location_name=final_location,
            country=country,
            latitude=final_lat,
            longitude=final_lon,
            start_date=new_start,
            end_date=new_end,
            weather_data=new_weather_data,
        )
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def delete_record(self, record_id: int) -> None:
        await self._store.delete(record_id)
        await self._session.commit()

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    async def get_all_for_export(
        self,
        location: str | None,
        start_date: date | None,
        end_date: date | None,
    ) -> list[WeatherRecord]:
        return await self._store.list_all_for_export(
            location=location,
            start_date=start_date,
            end_date=end_date,
        )