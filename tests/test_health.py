"""tests/test_health.py — Tests for health and readiness endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch


class TestHealth:
    """GET /health"""

    async def test_health_returns_ok(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert "service" in body

    async def test_readiness_with_db_up(self, client):
        with patch(
            "main.check_db_connectivity",
            new_callable=AsyncMock,
            return_value=True,
        ):
            response = await client.get("/health/ready")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ready"
        assert body["database"] == "ok"

    async def test_readiness_with_db_down(self, client):
        with patch(
            "main.check_db_connectivity",
            new_callable=AsyncMock,
            return_value=False,
        ):
            response = await client.get("/health/ready")
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "unavailable"
