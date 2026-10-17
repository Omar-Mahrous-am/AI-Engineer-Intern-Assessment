"""src/routes/weather_routes.py — FastAPI router for /api/v1/weather endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.controllers.weather_controller import WeatherController
from src.helpers.database import get_db
from src.helpers.response import paginated_response, success_response
from src.schemas.weather import (
    WeatherRecordResponse,
    WeatherSearchRequest,
    WeatherUpdateRequest,
)

router = APIRouter(prefix="/weather", tags=["Weather"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


def _controller(session: DbDep) -> WeatherController:
    return WeatherController(session)


ControllerDep = Annotated[WeatherController, Depends(_controller)]


# ---------------------------------------------------------------------------
# A. Search and Save
# ---------------------------------------------------------------------------


@router.post(
    "/search",
    status_code=status.HTTP_201_CREATED,
    summary="Search weather for a location and date range, then persist the result",
)
async def search_weather(
    body: WeatherSearchRequest,
    controller: ControllerDep,
) -> dict[str, Any]:
    record = await controller.search_and_save(body)
    return success_response(WeatherRecordResponse.model_validate(record).model_dump(), status_code=201)


# ---------------------------------------------------------------------------
# B. Current Weather
# ---------------------------------------------------------------------------


@router.get(
    "/current",
    summary="Get current weather for a location or coordinates",
)
async def current_weather(
    controller: ControllerDep,
    location: str | None = Query(default=None, description="City or location name"),
    latitude: float | None = Query(default=None, ge=-90.0, le=90.0),
    longitude: float | None = Query(default=None, ge=-180.0, le=180.0),
) -> dict[str, Any]:
    result = await controller.get_current_weather(location, latitude, longitude)
    return success_response(result)


# ---------------------------------------------------------------------------
# C. Forecast
# ---------------------------------------------------------------------------


@router.get(
    "/forecast",
    summary="Get a multi-day weather forecast (1–16 days)",
)
async def forecast(
    controller: ControllerDep,
    location: str | None = Query(default=None),
    latitude: float | None = Query(default=None, ge=-90.0, le=90.0),
    longitude: float | None = Query(default=None, ge=-180.0, le=180.0),
    days: int = Query(default=5, ge=1, le=16, description="Number of forecast days (1–16)"),
) -> dict[str, Any]:
    result = await controller.get_forecast(location, latitude, longitude, days)
    return success_response(result)


# ---------------------------------------------------------------------------
# D. History – List
# ---------------------------------------------------------------------------


@router.get(
    "/history",
    summary="List saved weather history with optional filters and pagination",
)
async def list_history(
    controller: ControllerDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    location: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
) -> dict[str, Any]:
    records, total = await controller.list_history(
        limit=limit,
        offset=offset,
        location=location,
        start_date=start_date,
        end_date=end_date,
    )
    items = [WeatherRecordResponse.model_validate(r).model_dump() for r in records]
    return paginated_response(items, total=total, limit=limit, offset=offset)


# ---------------------------------------------------------------------------
# D. History – Single Record
# ---------------------------------------------------------------------------


@router.get(
    "/history/{record_id}",
    summary="Get a specific saved weather record by ID",
)
async def get_history_record(
    record_id: int,
    controller: ControllerDep,
) -> dict[str, Any]:
    record = await controller.get_record(record_id)
    return success_response(WeatherRecordResponse.model_validate(record).model_dump())


# ---------------------------------------------------------------------------
# E. Update History
# ---------------------------------------------------------------------------


@router.put(
    "/history/{record_id}",
    summary="Update a saved weather record (re-fetches weather if location or dates change)",
)
async def update_history_record(
    record_id: int,
    body: WeatherUpdateRequest,
    controller: ControllerDep,
) -> dict[str, Any]:
    record = await controller.update_record(record_id, body)
    return success_response(WeatherRecordResponse.model_validate(record).model_dump())


# ---------------------------------------------------------------------------
# F. Delete History
# ---------------------------------------------------------------------------


@router.delete(
    "/history/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a saved weather record",
)
async def delete_history_record(
    record_id: int,
    controller: ControllerDep,
) -> Response:
    await controller.delete_record(record_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
