"""src/routes/export_routes.py — FastAPI router for /api/v1/exports endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.controllers.weather_controller import WeatherController
from src.helpers.database import get_db
from src.helpers.exceptions import UnsupportedExportFormatError
from src.helpers.export import (
    records_to_csv,
    records_to_json,
    safe_export_filename,
)
from src.schemas.weather import WeatherRecordResponse

router = APIRouter(prefix="/exports", tags=["Exports"])


def _controller(session: AsyncSession = Depends(get_db)) -> WeatherController:
    return WeatherController(session)


@router.get(
    "/weather",
    summary="Export weather history as JSON or CSV",
    responses={
        200: {
            "description": "File download",
            "content": {
                "application/json": {},
                "text/csv": {},
            },
        }
    },
)
async def export_weather(
    fmt: str = Query(
        default="json",
        alias="format",
        description="Export format: 'json' or 'csv'",
    ),
    location: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    controller: WeatherController = Depends(_controller),
) -> Response:
    fmt_lower = fmt.lower()
    if fmt_lower not in ("json", "csv"):
        raise UnsupportedExportFormatError(fmt)

    records = await controller.get_all_for_export(
        location=location,
        start_date=start_date,
        end_date=end_date,
    )

    serialized = [WeatherRecordResponse.model_validate(r).model_dump() for r in records]
    filename = safe_export_filename("weather_export", fmt_lower)

    if fmt_lower == "csv":
        content = records_to_csv(serialized)
        media_type = "text/csv"
    else:
        content = records_to_json(serialized)
        media_type = "application/json"

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )
