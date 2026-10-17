"""tests/test_weather_search.py — Tests for POST /api/v1/weather/search."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from tests.conftest import MOCK_GEO_RESULT, MOCK_WEATHER_DATA


class TestWeatherSearch:
    """POST /api/v1/weather/search"""

    async def test_valid_city_search(self, client, mock_geocode, mock_weather_range):
        """Valid city name + date range should return 201 with a persisted record."""
        response = await client.post(
            "/api/v1/weather/search",
            json={
                "location": "Mansoura, Egypt",
                "start_date": "2026-10-16",
                "end_date": "2026-10-20",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        record = data["data"]
        assert record["location_name"] == "Mansoura"
        assert record["country"] == "Egypt"
        assert record["start_date"] == "2026-10-16"
        assert record["end_date"] == "2026-10-20"
        assert "id" in record
        assert "weather_data" in record
        mock_geocode.assert_called_once_with("Mansoura, Egypt")
        mock_weather_range.assert_called_once()

    async def test_coordinate_based_search(self, client, mock_weather_range):
        """Direct latitude/longitude should work without geocoding."""
        response = await client.post(
            "/api/v1/weather/search",
            json={
                "latitude": 31.0364,
                "longitude": 31.3807,
                "start_date": "2026-10-16",
                "end_date": "2026-10-17",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        record = data["data"]
        assert record["latitude"] == pytest.approx(31.0364)
        assert record["longitude"] == pytest.approx(31.3807)

    async def test_missing_location_and_coords_returns_422(self, client):
        """Request without location or coords should fail validation."""
        response = await client.post(
            "/api/v1/weather/search",
            json={
                "start_date": "2026-10-16",
                "end_date": "2026-10-20",
            },
        )
        assert response.status_code == 422
        assert "error" in response.json()

    async def test_invalid_date_range_returns_422(self, client, mock_geocode):
        """start_date after end_date should fail with 422."""
        response = await client.post(
            "/api/v1/weather/search",
            json={
                "location": "Cairo",
                "start_date": "2026-10-20",
                "end_date": "2026-10-16",
            },
        )
        assert response.status_code == 422
        assert "error" in response.json()

    async def test_invalid_latitude_returns_422(self, client):
        """Latitude outside [-90, 90] should fail."""
        response = await client.post(
            "/api/v1/weather/search",
            json={
                "latitude": 200.0,
                "longitude": 31.0,
                "start_date": "2026-10-16",
                "end_date": "2026-10-17",
            },
        )
        assert response.status_code == 422

    async def test_invalid_longitude_returns_422(self, client):
        """Longitude outside [-180, 180] should fail."""
        response = await client.post(
            "/api/v1/weather/search",
            json={
                "latitude": 31.0,
                "longitude": -200.0,
                "start_date": "2026-10-16",
                "end_date": "2026-10-17",
            },
        )
        assert response.status_code == 422

    async def test_unknown_location_returns_404(self, client):
        """Geocoding a non-existent city should return 404."""
        with patch(
            "src.helpers.weather_client.geocode_location",
            new_callable=AsyncMock,
            side_effect=__import__(
                "src.helpers.exceptions", fromlist=["LocationNotFoundError"]
            ).LocationNotFoundError("XyzNonExistentCity123"),
        ):
            response = await client.post(
                "/api/v1/weather/search",
                json={
                    "location": "XyzNonExistentCity123",
                    "start_date": "2026-10-16",
                    "end_date": "2026-10-17",
                },
            )
        assert response.status_code == 404
        body = response.json()
        assert body["error"]["code"] == "LOCATION_NOT_FOUND"

    async def test_external_api_timeout_returns_504(self, client, mock_geocode):
        """Provider timeout should propagate as 504."""
        with patch(
            "src.helpers.weather_client.fetch_weather_for_range",
            new_callable=AsyncMock,
            side_effect=__import__(
                "src.helpers.exceptions", fromlist=["ExternalAPITimeoutError"]
            ).ExternalAPITimeoutError("timeout"),
        ):
            response = await client.post(
                "/api/v1/weather/search",
                json={
                    "location": "Mansoura",
                    "start_date": "2026-10-16",
                    "end_date": "2026-10-17",
                },
            )
        assert response.status_code == 504

    async def test_external_api_failure_returns_502(self, client, mock_geocode):
        """Provider HTTP error should return 502."""
        with patch(
            "src.helpers.weather_client.fetch_weather_for_range",
            new_callable=AsyncMock,
            side_effect=__import__(
                "src.helpers.exceptions", fromlist=["ExternalAPIError"]
            ).ExternalAPIError("upstream error"),
        ):
            response = await client.post(
                "/api/v1/weather/search",
                json={
                    "location": "Mansoura",
                    "start_date": "2026-10-16",
                    "end_date": "2026-10-17",
                },
            )
        assert response.status_code == 502
