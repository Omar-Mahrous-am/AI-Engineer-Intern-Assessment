"""src/models/__init__.py — Export all models so Alembic can detect them."""

from src.models.weather_record import WeatherRecord

__all__ = ["WeatherRecord"]
