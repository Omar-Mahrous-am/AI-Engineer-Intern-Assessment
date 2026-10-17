"""tests/test_persistence.py — Tests that records are actually persisted to the database."""

from __future__ import annotations

import pytest

from tests.conftest import MOCK_GEO_RESULT, MOCK_WEATHER_DATA


class TestDatabasePersistence:
    """Verify weather data is actually stored and retrievable."""

    async def test_record_persisted_after_search(self, client, mock_geocode, mock_weather_range):
        """Record created by /search must be retrievable via /history/{id}."""
        create_resp = await client.post(
            "/api/v1/weather/search",
            json={
                "location": "Mansoura",
                "start_date": "2026-10-16",
                "end_date": "2026-10-18",
            },
        )
        assert create_resp.status_code == 201
        record_id = create_resp.json()["data"]["id"]

        get_resp = await client.get(f"/api/v1/weather/history/{record_id}")
        assert get_resp.status_code == 200
        fetched = get_resp.json()["data"]
        assert fetched["id"] == record_id
        assert fetched["location_name"] == "Mansoura"
        assert fetched["weather_data"] is not None
        assert isinstance(fetched["weather_data"], dict)

    async def test_delete_removes_record_from_db(self, client, mock_geocode, mock_weather_range):
        """Deleted record must not be retrievable."""
        create_resp = await client.post(
            "/api/v1/weather/search",
            json={
                "location": "Mansoura",
                "start_date": "2026-10-16",
                "end_date": "2026-10-18",
            },
        )
        record_id = create_resp.json()["data"]["id"]

        del_resp = await client.delete(f"/api/v1/weather/history/{record_id}")
        assert del_resp.status_code == 204

        get_resp = await client.get(f"/api/v1/weather/history/{record_id}")
        assert get_resp.status_code == 404

    async def test_weather_data_json_structure(self, client, mock_geocode, mock_weather_range):
        """Persisted weather_data must have the normalized structure."""
        create_resp = await client.post(
            "/api/v1/weather/search",
            json={
                "location": "Mansoura",
                "start_date": "2026-10-16",
                "end_date": "2026-10-17",
            },
        )
        record = create_resp.json()["data"]
        wd = record["weather_data"]
        assert wd["provider"] == "open-meteo"
        assert "days" in wd
        assert isinstance(wd["days"], list)
