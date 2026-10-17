"""tests/conftest.py — Shared pytest fixtures using an in-memory SQLite test database."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

import src.models  # noqa: F401 - register models on Base.metadata
from src.helpers.database import Base, get_db

# ---------------------------------------------------------------------------
# In-memory SQLite engine for tests (no PostgreSQL required)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    """Provide a fresh in-memory SQLite engine for each test."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh database session wired to the test engine."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an HTTPX AsyncClient wired to the FastAPI app.
    The get_db dependency is overridden to use the test session.
    """
    from main import app

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Shared mock payloads
# ---------------------------------------------------------------------------

MOCK_GEO_RESULT: dict[str, Any] = {
    "name": "Mansoura",
    "country": "Egypt",
    "latitude": 31.0364,
    "longitude": 31.3807,
    "admin1": "Ad Daqahliyah",
    "timezone": "Africa/Cairo",
}

MOCK_WEATHER_DATA: dict[str, Any] = {
    "provider": "open-meteo",
    "type": "forecast",
    "latitude": 31.0364,
    "longitude": 31.3807,
    "timezone": "Africa/Cairo",
    "elevation": 7.0,
    "days": [
        {
            "date": "2026-10-16",
            "temperature_max": 28.5,
            "temperature_min": 20.0,
            "temperature_unit": "°C",
            "weather_code": 1,
            "weather_description": "Mainly clear",
            "precipitation_sum": 0.0,
            "precipitation_unit": "mm",
            "wind_speed_max": 15.0,
            "wind_speed_unit": "km/h",
        }
    ],
}

MOCK_CURRENT_DATA: dict[str, Any] = {
    "provider": "open-meteo",
    "type": "current",
    "time": "2026-10-16T12:00",
    "temperature": 26.5,
    "temperature_unit": "°C",
    "apparent_temperature": 25.0,
    "relative_humidity": 60,
    "wind_speed": 12.0,
    "wind_speed_unit": "km/h",
    "weather_code": 1,
    "weather_description": "Mainly clear",
    "precipitation": 0.0,
    "latitude": 31.0364,
    "longitude": 31.3807,
    "timezone": "Africa/Cairo",
    "elevation": 7.0,
}


# ---------------------------------------------------------------------------
# Reusable mock fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_geocode():
    """Patch geocode_location to avoid real HTTP calls."""
    with patch(
        "src.helpers.weather_client.geocode_location",
        new_callable=AsyncMock,
        return_value=MOCK_GEO_RESULT,
    ) as m:
        yield m


@pytest.fixture
def mock_weather_range():
    """Patch fetch_weather_for_range to avoid real HTTP calls."""
    with patch(
        "src.helpers.weather_client.fetch_weather_for_range",
        new_callable=AsyncMock,
        return_value=MOCK_WEATHER_DATA,
    ) as m:
        yield m


@pytest.fixture
def mock_current_weather():
    """Patch fetch_current_weather to avoid real HTTP calls."""
    with patch(
        "src.helpers.weather_client.fetch_current_weather",
        new_callable=AsyncMock,
        return_value=MOCK_CURRENT_DATA,
    ) as m:
        yield m


@pytest.fixture
def mock_forecast():
    """Patch fetch_forecast to avoid real HTTP calls."""
    with patch(
        "src.helpers.weather_client.fetch_forecast",
        new_callable=AsyncMock,
        return_value=MOCK_WEATHER_DATA,
    ) as m:
        yield m
