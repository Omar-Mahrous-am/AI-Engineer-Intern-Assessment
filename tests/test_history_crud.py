"""tests/test_history_crud.py — CRUD tests for weather history endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from tests.conftest import MOCK_GEO_RESULT, MOCK_WEATHER_DATA


async def _create_record(client, mock_geocode, mock_weather_range) -> int:
    """Helper: POST a record and return its id."""
    resp = await client.post(
        "/api/v1/weather/search",
        json={
            "location": "Mansoura, Egypt",
            "start_date": "2026-10-16",
            "end_date": "2026-10-18",
        },
    )
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


class TestHistoryList:
    """GET /api/v1/weather/history"""

    async def test_list_returns_created_records(self, client, mock_geocode, mock_weather_range):
        await _create_record(client, mock_geocode, mock_weather_range)
        response = await client.get("/api/v1/weather/history")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) >= 1

    async def test_list_pagination(self, client, mock_geocode, mock_weather_range):
        response = await client.get("/api/v1/weather/history?limit=1&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) <= 1

    async def test_list_location_filter(self, client, mock_geocode, mock_weather_range):
        await _create_record(client, mock_geocode, mock_weather_range)
        response = await client.get("/api/v1/weather/history?location=mansoura")
        assert response.status_code == 200
        data = response.json()
        for record in data["data"]:
            assert "mansoura" in record["location_name"].lower()


class TestHistoryGetOne:
    """GET /api/v1/weather/history/{record_id}"""

    async def test_get_existing_record(self, client, mock_geocode, mock_weather_range):
        record_id = await _create_record(client, mock_geocode, mock_weather_range)
        response = await client.get(f"/api/v1/weather/history/{record_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == record_id

    async def test_get_nonexistent_record_returns_404(self, client):
        response = await client.get("/api/v1/weather/history/999999")
        assert response.status_code == 404
        body = response.json()
        assert body["error"]["code"] == "RECORD_NOT_FOUND"


class TestHistoryUpdate:
    """PUT /api/v1/weather/history/{record_id}"""

    async def test_update_record(self, client, mock_geocode, mock_weather_range):
        record_id = await _create_record(client, mock_geocode, mock_weather_range)

        with patch(
            "src.helpers.weather_client.fetch_weather_for_range",
            new_callable=AsyncMock,
            return_value=MOCK_WEATHER_DATA,
        ):
            with patch(
                "src.helpers.weather_client.geocode_location",
                new_callable=AsyncMock,
                return_value={**MOCK_GEO_RESULT, "name": "Cairo", "country": "Egypt"},
            ):
                response = await client.put(
                    f"/api/v1/weather/history/{record_id}",
                    json={"location": "Cairo, Egypt"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["location_name"] == "Cairo"

    async def test_update_nonexistent_record_returns_404(self, client):
        response = await client.put(
            "/api/v1/weather/history/999999",
            json={"location": "Cairo"},
        )
        assert response.status_code == 404

    async def test_update_empty_body_returns_422(self, client, mock_geocode, mock_weather_range):
        record_id = await _create_record(client, mock_geocode, mock_weather_range)
        response = await client.put(
            f"/api/v1/weather/history/{record_id}",
            json={},
        )
        assert response.status_code == 422

    async def test_update_invalid_date_range_returns_422(self, client, mock_geocode, mock_weather_range):
        record_id = await _create_record(client, mock_geocode, mock_weather_range)
        response = await client.put(
            f"/api/v1/weather/history/{record_id}",
            json={"start_date": "2026-10-20", "end_date": "2026-10-16"},
        )
        assert response.status_code == 422


class TestHistoryDelete:
    """DELETE /api/v1/weather/history/{record_id}"""

    async def test_delete_existing_record_returns_204(self, client, mock_geocode, mock_weather_range):
        record_id = await _create_record(client, mock_geocode, mock_weather_range)
        response = await client.delete(f"/api/v1/weather/history/{record_id}")
        assert response.status_code == 204

        # Confirm it's gone
        get_resp = await client.get(f"/api/v1/weather/history/{record_id}")
        assert get_resp.status_code == 404

    async def test_delete_nonexistent_record_returns_404(self, client):
        response = await client.delete("/api/v1/weather/history/999999")
        assert response.status_code == 404
