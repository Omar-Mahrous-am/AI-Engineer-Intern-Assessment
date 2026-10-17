"""tests/test_current_forecast.py — Tests for current weather and forecast endpoints."""

from __future__ import annotations


class TestCurrentWeather:
    """GET /api/v1/weather/current"""

    async def test_current_by_location(self, client, mock_geocode, mock_current_weather):
        response = await client.get("/api/v1/weather/current?location=Mansoura")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["location_name"] == "Mansoura"
        assert "weather" in data["data"]
        mock_geocode.assert_called_once_with("Mansoura")
        mock_current_weather.assert_called_once()

    async def test_current_by_coordinates(self, client, mock_current_weather):
        response = await client.get(
            "/api/v1/weather/current?latitude=31.0364&longitude=31.3807"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "weather" in data["data"]

    async def test_current_no_params_returns_400(self, client):
        response = await client.get("/api/v1/weather/current")
        assert response.status_code == 400

    async def test_current_invalid_lat_returns_422(self, client):
        response = await client.get(
            "/api/v1/weather/current?latitude=999&longitude=31.0"
        )
        assert response.status_code == 422


class TestForecast:
    """GET /api/v1/weather/forecast"""

    async def test_forecast_by_location(self, client, mock_geocode, mock_forecast):
        response = await client.get("/api/v1/weather/forecast?location=Mansoura&days=5")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["days_requested"] == 5
        assert "forecast" in data["data"]

    async def test_forecast_by_coordinates(self, client, mock_forecast):
        response = await client.get(
            "/api/v1/weather/forecast?latitude=31.0364&longitude=31.3807&days=3"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["days_requested"] == 3

    async def test_forecast_invalid_days_returns_422(self, client, mock_geocode):
        response = await client.get("/api/v1/weather/forecast?location=Cairo&days=99")
        assert response.status_code == 422

    async def test_forecast_no_params_returns_400(self, client):
        response = await client.get("/api/v1/weather/forecast")
        assert response.status_code == 400
