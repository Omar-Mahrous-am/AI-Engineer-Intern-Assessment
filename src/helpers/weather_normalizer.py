"""src/helpers/weather_normalizer.py — Pure normalization helpers for weather API responses."""

from __future__ import annotations

from typing import Any

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


def _wmo_description(code: int | None) -> str | None:
    if code is None:
        return None
    try:
        return _WMO_CODES.get(int(code), f"Weather code {code}")
    except (ValueError, TypeError):
        return None


def normalize_current(weather: dict | None) -> dict:
    """
    Normalize current weather to a flat dict with canonical keys.

    Accepts:
      - Flat dict containing keys like temperature, relative_humidity, etc.
      - Open-Meteo raw shape containing 'current' and optional 'current_units'.
      - None or any other type (returns default dict with None values).
    Never raises an exception.
    """
    if not isinstance(weather, dict):
        return {
            "temperature": None,
            "apparent_temperature": None,
            "relative_humidity": None,
            "wind_speed": None,
            "precipitation": None,
            "weather_code": None,
            "weather_description": None,
            "temperature_unit": "°C",
            "wind_speed_unit": "km/h",
            "timezone": None,
        }

    current = weather.get("current") if isinstance(weather.get("current"), dict) else {}
    units = weather.get("current_units") if isinstance(weather.get("current_units"), dict) else {}

    # Temperature
    temperature = weather.get("temperature")
    if temperature is None:
        temperature = current.get("temperature_2m", current.get("temperature"))

    # Apparent temperature
    apparent_temperature = weather.get("apparent_temperature")
    if apparent_temperature is None:
        apparent_temperature = current.get("apparent_temperature")

    # Relative humidity
    relative_humidity = weather.get("relative_humidity")
    if relative_humidity is None:
        relative_humidity = current.get("relative_humidity_2m", current.get("relative_humidity"))

    # Wind speed
    wind_speed = weather.get("wind_speed")
    if wind_speed is None:
        wind_speed = current.get("wind_speed_10m", current.get("wind_speed"))

    # Precipitation
    precipitation = weather.get("precipitation")
    if precipitation is None:
        precipitation = current.get("precipitation")

    # Weather code
    weather_code = weather.get("weather_code")
    if weather_code is None:
        weather_code = current.get("weather_code")

    # Weather description
    weather_description = weather.get("weather_description")
    if weather_description is None:
        weather_description = current.get("weather_description")
    if weather_description is None and weather_code is not None:
        weather_description = _wmo_description(weather_code)

    # Units
    temperature_unit = (
        weather.get("temperature_unit")
        or units.get("temperature_2m")
        or units.get("temperature")
        or "°C"
    )
    wind_speed_unit = (
        weather.get("wind_speed_unit")
        or units.get("wind_speed_10m")
        or units.get("wind_speed")
        or "km/h"
    )

    # Timezone
    timezone = weather.get("timezone") or current.get("timezone")

    return {
        "temperature": temperature,
        "apparent_temperature": apparent_temperature,
        "relative_humidity": relative_humidity,
        "wind_speed": wind_speed,
        "precipitation": precipitation,
        "weather_code": weather_code,
        "weather_description": weather_description,
        "temperature_unit": temperature_unit,
        "wind_speed_unit": wind_speed_unit,
        "timezone": timezone,
    }


def normalize_forecast(forecast: Any) -> list[dict]:
    """
    Normalize forecast data into a list of per-day dicts.

    Accepts:
      - list of day dicts
      - dict with 'days': list of day dicts
      - dict with 'daily': dict of parallel arrays (Open-Meteo raw shape)
      - returns [] for anything else
    Never raises an exception.
    """
    if not forecast:
        return []

    # 1. Open-Meteo raw shape: {"daily": {"time": [...], ...}}
    if isinstance(forecast, dict) and isinstance(forecast.get("daily"), dict):
        daily = forecast["daily"]
        times = daily.get("time")
        if not isinstance(times, list):
            return []

        max_temps = (
            daily.get("temperature_2m_max")
            if isinstance(daily.get("temperature_2m_max"), list)
            else (
                daily.get("temperature_max")
                if isinstance(daily.get("temperature_max"), list)
                else []
            )
        )
        min_temps = (
            daily.get("temperature_2m_min")
            if isinstance(daily.get("temperature_2m_min"), list)
            else (
                daily.get("temperature_min")
                if isinstance(daily.get("temperature_min"), list)
                else []
            )
        )
        codes = daily.get("weather_code") if isinstance(daily.get("weather_code"), list) else []
        precips = (
            daily.get("precipitation_sum")
            if isinstance(daily.get("precipitation_sum"), list)
            else (
                daily.get("precipitation")
                if isinstance(daily.get("precipitation"), list)
                else []
            )
        )

        days_list: list[dict] = []
        for i, t in enumerate(times):
            days_list.append({
                "date": t,
                "temperature_max": max_temps[i] if i < len(max_temps) else None,
                "temperature_min": min_temps[i] if i < len(min_temps) else None,
                "weather_code": codes[i] if i < len(codes) else None,
                "precipitation_sum": precips[i] if i < len(precips) else None,
            })
        return days_list

    # 2. Dict with "days" or "forecast"
    raw_days: Any = None
    if isinstance(forecast, dict):
        if isinstance(forecast.get("days"), list):
            raw_days = forecast["days"]
        elif isinstance(forecast.get("forecast"), list):
            raw_days = forecast["forecast"]
        elif isinstance(forecast.get("forecast"), dict) and isinstance(forecast["forecast"].get("days"), list):
            raw_days = forecast["forecast"]["days"]
        else:
            return []
    elif isinstance(forecast, list):
        raw_days = forecast
    else:
        return []

    days_list = []
    for day in raw_days:
        if not isinstance(day, dict):
            continue
        date_val = day.get("date") if day.get("date") is not None else day.get("time")
        t_max = (
            day.get("temperature_max")
            if day.get("temperature_max") is not None
            else day.get("temperature_2m_max")
        )
        t_min = (
            day.get("temperature_min")
            if day.get("temperature_min") is not None
            else day.get("temperature_2m_min")
        )
        code_val = day.get("weather_code")
        precip_val = (
            day.get("precipitation_sum")
            if day.get("precipitation_sum") is not None
            else day.get("precipitation")
        )

        days_list.append({
            "date": date_val,
            "temperature_max": t_max,
            "temperature_min": t_min,
            "weather_code": code_val,
            "precipitation_sum": precip_val,
        })

    return days_list
