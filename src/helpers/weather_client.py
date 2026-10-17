"""src/helpers/weather_client.py — Async HTTPX clients for Open-Meteo geocoding and weather APIs."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any

import httpx

from src.helpers.config import get_settings
from src.helpers.exceptions import (
    ExternalAPIError,
    ExternalAPITimeoutError,
    LocationNotFoundError,
)
from src.helpers.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

GEOCODING_API = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_API = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_API = "https://archive-api.open-meteo.com/v1/archive"

# Open-Meteo archive data starts from 1940-01-01 and has a ~5-day lag
ARCHIVE_START = date(1940, 1, 1)
ARCHIVE_LAG_DAYS = 5  # archive may not have data within the last ~5 days

# Maximum retry attempts for transient failures
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 1.0

_CURRENT_HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "wind_speed_10m",
    "weather_code",
    "precipitation",
]

_FORECAST_DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "weather_code",
    "precipitation_sum",
    "wind_speed_10m_max",
]

_CURRENT_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "wind_speed_10m",
    "weather_code",
    "precipitation",
]


async def _get(url: str, params: dict[str, Any]) -> dict[str, Any]:
    """Execute an HTTPX GET with retries and return the JSON body."""
    timeout = httpx.Timeout(settings.http_timeout_seconds)
    last_exc: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as exc:
            last_exc = exc
            logger.warning("Request to %s timed out (attempt %d)", url, attempt + 1)
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY_SECONDS)
        except httpx.HTTPStatusError as exc:
            logger.error(
                "HTTP %d from %s: %s",
                exc.response.status_code,
                url,
                exc.response.text[:200],
            )
            raise ExternalAPIError(
                f"Weather provider returned HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            last_exc = exc
            logger.warning("HTTP error from %s (attempt %d): %s", url, attempt + 1, exc)
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY_SECONDS)

    if isinstance(last_exc, httpx.TimeoutException):
        raise ExternalAPITimeoutError(
            "The weather provider did not respond in time. Please try again later."
        )
    raise ExternalAPIError(
        "Could not reach the weather provider after multiple attempts."
    ) from last_exc


async def geocode_location(location_name: str) -> dict[str, Any]:
    """
    Resolve a location name to coordinates via Open-Meteo Geocoding.

    Returns the best matching result dict with keys:
        name, country, latitude, longitude, admin1, timezone
    Raises LocationNotFoundError if nothing is found.
    """
    params = {
        "name": location_name,
        "count": 5,
        "language": "en",
        "format": "json",
    }
    data = await _get(GEOCODING_API, params)
    results: list[dict[str, Any]] = data.get("results") or []
    if not results:
        raise LocationNotFoundError(location_name)
    return results[0]


async def fetch_current_weather(
    latitude: float, longitude: float
) -> dict[str, Any]:
    """Fetch current conditions at the given coordinates."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join(_CURRENT_VARS),
        "timezone": "auto",
    }
    data = await _get(FORECAST_API, params)
    return _normalize_current(data)


async def fetch_forecast(
    latitude: float, longitude: float, days: int = 5
) -> dict[str, Any]:
    """Fetch a multi-day daily forecast (1–16 days supported by Open-Meteo)."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ",".join(_FORECAST_DAILY_VARS),
        "forecast_days": min(days, 16),
        "timezone": "auto",
    }
    data = await _get(FORECAST_API, params)
    return _normalize_forecast(data)


async def fetch_weather_for_range(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    """
    Fetch weather for an arbitrary date range, routing to the archive or
    forecast API as appropriate.
    """
    today = date.today()
    archive_cutoff = today - timedelta(days=ARCHIVE_LAG_DAYS)

    if end_date <= archive_cutoff:
        # Entirely historical
        return await _fetch_archive(latitude, longitude, start_date, end_date)

    if start_date > today:
        # Entirely in the future
        return await _fetch_forecast_range(latitude, longitude, start_date, end_date, today)

    # Spans present: split and merge
    tasks: list[Any] = []
    has_historical = start_date <= archive_cutoff
    has_forecast = end_date > today

    if has_historical:
        tasks.append(
            _fetch_archive(latitude, longitude, start_date, min(end_date, archive_cutoff))
        )
    if has_forecast:
        tasks.append(
            _fetch_forecast_range(latitude, longitude, max(start_date, today + timedelta(days=1)), end_date, today)
        )
    if not has_historical and not has_forecast:
        # Current period — use forecast with forecast_days=1
        tasks.append(
            _fetch_forecast_range(latitude, longitude, start_date, end_date, today)
        )

    results = await asyncio.gather(*tasks)
    return _merge_daily_results(results)


async def _fetch_archive(
    latitude: float, longitude: float, start_date: date, end_date: date
) -> dict[str, Any]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": ",".join(_FORECAST_DAILY_VARS),
        "timezone": "auto",
    }
    data = await _get(ARCHIVE_API, params)
    return _normalize_forecast(data)


async def _fetch_forecast_range(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
    today: date,
) -> dict[str, Any]:
    days_ahead = (end_date - today).days + 1
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ",".join(_FORECAST_DAILY_VARS),
        "forecast_days": min(max(days_ahead, 1), 16),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "timezone": "auto",
    }
    data = await _get(FORECAST_API, params)
    return _normalize_forecast(data)


def _normalize_current(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert the Open-Meteo /forecast current block into a flat dict."""
    current: dict[str, Any] = raw.get("current", {})
    units: dict[str, Any] = raw.get("current_units", {})
    return {
        "provider": "open-meteo",
        "type": "current",
        "time": current.get("time"),
        "temperature": current.get("temperature_2m"),
        "temperature_unit": units.get("temperature_2m", "°C"),
        "apparent_temperature": current.get("apparent_temperature"),
        "relative_humidity": current.get("relative_humidity_2m"),
        "wind_speed": current.get("wind_speed_10m"),
        "wind_speed_unit": units.get("wind_speed_10m", "km/h"),
        "weather_code": current.get("weather_code"),
        "weather_description": _wmo_description(current.get("weather_code")),
        "precipitation": current.get("precipitation"),
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "timezone": raw.get("timezone"),
        "elevation": raw.get("elevation"),
    }


def _normalize_forecast(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert Open-Meteo daily arrays into a list of day dicts."""
    daily: dict[str, Any] = raw.get("daily", {})
    daily_units: dict[str, Any] = raw.get("daily_units", {})
    times: list[str] = daily.get("time", [])

    days: list[dict[str, Any]] = []
    for i, day_str in enumerate(times):
        days.append(
            {
                "date": day_str,
                "temperature_max": _nth(daily.get("temperature_2m_max"), i),
                "temperature_min": _nth(daily.get("temperature_2m_min"), i),
                "temperature_unit": daily_units.get("temperature_2m_max", "°C"),
                "weather_code": _nth(daily.get("weather_code"), i),
                "weather_description": _wmo_description(_nth(daily.get("weather_code"), i)),
                "precipitation_sum": _nth(daily.get("precipitation_sum"), i),
                "precipitation_unit": daily_units.get("precipitation_sum", "mm"),
                "wind_speed_max": _nth(daily.get("wind_speed_10m_max"), i),
                "wind_speed_unit": daily_units.get("wind_speed_10m_max", "km/h"),
            }
        )

    return {
        "provider": "open-meteo",
        "type": "forecast",
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "timezone": raw.get("timezone"),
        "elevation": raw.get("elevation"),
        "days": days,
    }


def _merge_daily_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge multiple normalized forecast results into a single result."""
    if not results:
        return {"provider": "open-meteo", "type": "forecast", "days": []}
    merged = dict(results[0])
    all_days: list[dict[str, Any]] = []
    for r in results:
        all_days.extend(r.get("days", []))
    # De-duplicate by date and sort
    seen: set[str] = set()
    unique_days: list[dict[str, Any]] = []
    for day in sorted(all_days, key=lambda d: d["date"]):
        if day["date"] not in seen:
            seen.add(day["date"])
            unique_days.append(day)
    merged["days"] = unique_days
    return merged


def _nth(lst: list[Any] | None, index: int) -> Any:
    if lst is None or index >= len(lst):
        return None
    return lst[index]


# WMO Weather Interpretation Codes (WW)
_WMO_CODES: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Heavy freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def _wmo_description(code: int | None) -> str:
    if code is None:
        return "Unknown"
    return _WMO_CODES.get(int(code), f"Weather code {code}")
