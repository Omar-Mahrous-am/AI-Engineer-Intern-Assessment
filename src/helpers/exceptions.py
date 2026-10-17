"""src/helpers/exceptions.py — Custom application exceptions and HTTP error helpers."""

from __future__ import annotations

from fastapi import HTTPException, status


class AppError(Exception):
    """Base class for all application-level exceptions."""

    code: str = "INTERNAL_ERROR"
    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class LocationNotFoundError(AppError):
    code = "LOCATION_NOT_FOUND"
    http_status = status.HTTP_404_NOT_FOUND

    def __init__(self, location: str) -> None:
        super().__init__(f"The location '{location}' could not be found.")


class InvalidCoordinatesError(AppError):
    code = "INVALID_COORDINATES"
    http_status = status.HTTP_400_BAD_REQUEST


class InvalidDateRangeError(AppError):
    code = "INVALID_DATE_RANGE"
    http_status = status.HTTP_400_BAD_REQUEST


class WeatherRecordNotFoundError(AppError):
    code = "RECORD_NOT_FOUND"
    http_status = status.HTTP_404_NOT_FOUND

    def __init__(self, record_id: int) -> None:
        super().__init__(f"Weather record with id={record_id} was not found.")


class ExternalAPIError(AppError):
    code = "EXTERNAL_API_ERROR"
    http_status = status.HTTP_502_BAD_GATEWAY


class ExternalAPITimeoutError(AppError):
    code = "EXTERNAL_API_TIMEOUT"
    http_status = status.HTTP_504_GATEWAY_TIMEOUT


class ServiceUnavailableError(AppError):
    code = "SERVICE_UNAVAILABLE"
    http_status = status.HTTP_503_SERVICE_UNAVAILABLE


class UnsupportedExportFormatError(AppError):
    code = "UNSUPPORTED_EXPORT_FORMAT"
    http_status = status.HTTP_400_BAD_REQUEST

    def __init__(self, fmt: str) -> None:
        super().__init__(f"Export format '{fmt}' is not supported. Use 'json' or 'csv'.")


class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    http_status = status.HTTP_400_BAD_REQUEST
