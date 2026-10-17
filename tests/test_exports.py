"""tests/test_exports.py — Tests for GET /api/v1/exports/weather."""

from __future__ import annotations

import csv
import io


async def _seed_record(client, mock_geocode, mock_weather_range) -> dict:
    resp = await client.post(
        "/api/v1/weather/search",
        json={
            "location": "Mansoura, Egypt",
            "start_date": "2026-10-16",
            "end_date": "2026-10-18",
        },
    )
    assert resp.status_code == 201
    return resp.json()["data"]


class TestExports:
    """GET /api/v1/exports/weather"""

    async def test_json_export_returns_json_file(self, client, mock_geocode, mock_weather_range):
        await _seed_record(client, mock_geocode, mock_weather_range)
        response = await client.get("/api/v1/exports/weather?format=json")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        assert "attachment" in response.headers.get("content-disposition", "")
        assert ".json" in response.headers.get("content-disposition", "")
        # Should be valid JSON list
        data = response.json()
        assert isinstance(data, list)

    async def test_csv_export_returns_csv_file(self, client, mock_geocode, mock_weather_range):
        await _seed_record(client, mock_geocode, mock_weather_range)
        response = await client.get("/api/v1/exports/weather?format=csv")
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers.get("content-disposition", "")
        assert ".csv" in response.headers.get("content-disposition", "")

        # Should be parseable as CSV
        text = response.text
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        assert len(rows) >= 1
        assert "location_name" in reader.fieldnames

    async def test_unsupported_format_returns_400(self, client):
        response = await client.get("/api/v1/exports/weather?format=xlsx")
        assert response.status_code == 400
        body = response.json()
        assert body["error"]["code"] == "UNSUPPORTED_EXPORT_FORMAT"

    async def test_csv_export_with_location_filter(self, client, mock_geocode, mock_weather_range):
        await _seed_record(client, mock_geocode, mock_weather_range)
        response = await client.get("/api/v1/exports/weather?format=csv&location=mansoura")
        assert response.status_code == 200
        text = response.text
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        for row in rows:
            assert "mansoura" in row["location_name"].lower()

    async def test_json_export_empty_returns_empty_list(self, client):
        """When no records match filter, export returns empty list."""
        response = await client.get(
            "/api/v1/exports/weather?format=json&location=NonExistentCityXyz999"
        )
        assert response.status_code == 200
        data = response.json()
        assert data == []

    async def test_csv_export_empty_returns_empty_body(self, client):
        """When no records match, CSV body is empty."""
        response = await client.get(
            "/api/v1/exports/weather?format=csv&location=NonExistentCityXyz999"
        )
        assert response.status_code == 200
        assert response.content == b""
