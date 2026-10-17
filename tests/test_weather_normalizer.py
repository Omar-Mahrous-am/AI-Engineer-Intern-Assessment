"""tests/test_weather_normalizer.py — Unit tests for normalize_current and normalize_forecast."""

from __future__ import annotations

import pytest

from src.helpers.weather_normalizer import normalize_current, normalize_forecast


class TestNormalizeCurrent:
    """Test suite for normalize_current."""

    def test_sample_cairo_weather_json(self):
        weather_payload = {
            "temperature": 23.6,
            "temperature_unit": "°C",
            "apparent_temperature": 23.6,
            "relative_humidity": 46,
            "wind_speed": 3.1,
            "wind_speed_unit": "km/h",
            "weather_code": 1,
            "weather_description": "Mainly clear",
            "precipitation": 0.0,
            "timezone": "Africa/Cairo",
        }
        res = normalize_current(weather_payload)

        assert res["temperature"] == 23.6
        assert res["relative_humidity"] == 46
        assert res["wind_speed"] == 3.1
        assert res["precipitation"] == 0.0
        assert res["weather_code"] == 1
        assert res["weather_description"] == "Mainly clear"
        assert res["apparent_temperature"] == 23.6
        assert res["temperature_unit"] == "°C"
        assert res["wind_speed_unit"] == "km/h"
        assert res["timezone"] == "Africa/Cairo"

    def test_raw_open_meteo_shape(self):
        raw_payload = {
            "current": {
                "temperature_2m": 23.6,
                "apparent_temperature": 23.6,
                "relative_humidity_2m": 46,
                "wind_speed_10m": 3.1,
                "precipitation": 0.0,
                "weather_code": 1,
            },
            "current_units": {
                "temperature_2m": "°C",
                "wind_speed_10m": "km/h",
            },
            "timezone": "Africa/Cairo",
        }
        res = normalize_current(raw_payload)

        assert res["temperature"] == 23.6
        assert res["apparent_temperature"] == 23.6
        assert res["relative_humidity"] == 46
        assert res["wind_speed"] == 3.1
        assert res["precipitation"] == 0.0
        assert res["weather_code"] == 1
        assert res["weather_description"] == "Mainly clear"
        assert res["temperature_unit"] == "°C"
        assert res["wind_speed_unit"] == "km/h"
        assert res["timezone"] == "Africa/Cairo"

    def test_none_input_does_not_raise(self):
        res = normalize_current(None)
        assert res["temperature"] is None
        assert res["apparent_temperature"] is None
        assert res["relative_humidity"] is None
        assert res["wind_speed"] is None
        assert res["precipitation"] is None
        assert res["weather_code"] is None
        assert res["weather_description"] is None
        assert res["temperature_unit"] == "°C"
        assert res["wind_speed_unit"] == "km/h"
        assert res["timezone"] is None

    def test_empty_dict_does_not_raise(self):
        res = normalize_current({})
        assert res["temperature"] is None
        assert res["temperature_unit"] == "°C"
        assert res["wind_speed_unit"] == "km/h"


class TestNormalizeForecast:
    """Test suite for normalize_forecast."""

    def test_list_input(self):
        day_list = [
            {
                "date": "2026-10-16",
                "temperature_max": 28.5,
                "temperature_min": 20.0,
                "weather_code": 1,
                "precipitation_sum": 0.0,
            },
            {
                "date": "2026-10-17",
                "temperature_max": 27.0,
                "temperature_min": 19.5,
                "weather_code": 2,
                "precipitation_sum": 1.2,
            },
        ]
        res = normalize_forecast(day_list)
        assert len(res) == 2
        assert res[0]["date"] == "2026-10-16"
        assert res[0]["temperature_max"] == 28.5
        assert res[0]["temperature_min"] == 20.0
        assert res[0]["weather_code"] == 1
        assert res[0]["precipitation_sum"] == 0.0
        assert res[1]["date"] == "2026-10-17"

    def test_days_dict_input(self):
        forecast_dict = {
            "days": [
                {
                    "date": "2026-10-16",
                    "temperature_max": 28.5,
                    "temperature_min": 20.0,
                    "weather_code": 1,
                    "precipitation_sum": 0.0,
                }
            ]
        }
        res = normalize_forecast(forecast_dict)
        assert len(res) == 1
        assert res[0]["date"] == "2026-10-16"
        assert res[0]["temperature_max"] == 28.5
        assert res[0]["temperature_min"] == 20.0
        assert res[0]["weather_code"] == 1
        assert res[0]["precipitation_sum"] == 0.0

    def test_open_meteo_daily_arrays_input(self):
        raw_daily = {
            "daily": {
                "time": ["2026-10-16", "2026-10-17"],
                "temperature_2m_max": [28.5, 27.0],
                "temperature_2m_min": [20.0, 19.5],
                "weather_code": [1, 2],
                "precipitation_sum": [0.0, 1.2],
            }
        }
        res = normalize_forecast(raw_daily)
        assert len(res) == 2
        assert res[0] == {
            "date": "2026-10-16",
            "temperature_max": 28.5,
            "temperature_min": 20.0,
            "weather_code": 1,
            "precipitation_sum": 0.0,
        }
        assert res[1] == {
            "date": "2026-10-17",
            "temperature_max": 27.0,
            "temperature_min": 19.5,
            "weather_code": 2,
            "precipitation_sum": 1.2,
        }

    def test_invalid_input_returns_empty_list(self):
        assert normalize_forecast(None) == []
        assert normalize_forecast({}) == []
        assert normalize_forecast("invalid") == []
        assert normalize_forecast(123) == []
