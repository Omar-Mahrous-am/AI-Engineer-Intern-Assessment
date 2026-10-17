"""src/schemas/weather.py — Pydantic v2 request and response schemas for weather endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class WeatherSearchRequest(BaseModel):
    """Request body for POST /api/v1/weather/search."""

    location: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="City or location name (e.g. 'Mansoura, Egypt').",
        examples=["Mansoura, Egypt"],
    )
    latitude: float | None = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="Latitude in decimal degrees (-90 to 90).",
    )
    longitude: float | None = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="Longitude in decimal degrees (-180 to 180).",
    )
    start_date: date = Field(..., description="Start date (YYYY-MM-DD).")
    end_date: date = Field(..., description="End date (YYYY-MM-DD, inclusive).")

    @model_validator(mode="after")
    def check_location_or_coords(self) -> "WeatherSearchRequest":
        has_location = bool(self.location)
        has_coords = self.latitude is not None and self.longitude is not None

        if not has_location and not has_coords:
            raise ValueError(
                "Provide either 'location' or both 'latitude' and 'longitude'."
            )
        if self.start_date > self.end_date:
            raise ValueError("'start_date' must be on or before 'end_date'.")
        return self


class WeatherUpdateRequest(BaseModel):
    """Request body for PUT /api/v1/weather/history/{record_id}."""

    location: str | None = Field(default=None, min_length=1, max_length=200)
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> "WeatherUpdateRequest":
        if all(
            v is None
            for v in [
                self.location,
                self.latitude,
                self.longitude,
                self.start_date,
                self.end_date,
            ]
        ):
            raise ValueError("Provide at least one field to update.")
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("'start_date' must be on or before 'end_date'.")
        return self


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class WeatherRecordResponse(BaseModel):
    """Response schema for a persisted weather record."""

    id: int
    location_name: str
    country: str | None
    latitude: float
    longitude: float
    start_date: date
    end_date: date
    weather_data: dict[str, Any]
    provider: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WeatherRecordListResponse(BaseModel):
    """Paginated list of weather records."""

    data: list[WeatherRecordResponse]
    pagination: dict[str, Any]
    success: bool = True


class CurrentWeatherResponse(BaseModel):
    """Response for GET /api/v1/weather/current."""

    location_name: str
    country: str | None = None
    latitude: float
    longitude: float
    weather: dict[str, Any]
    success: bool = True


class ForecastResponse(BaseModel):
    """Response for GET /api/v1/weather/forecast."""

    location_name: str
    country: str | None = None
    latitude: float
    longitude: float
    days_requested: int
    forecast: dict[str, Any]
    success: bool = True
