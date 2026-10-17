"""src/helpers/response.py — Standardised success and error response builders."""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse


def success_response(data: Any, *, status_code: int = 200) -> dict[str, Any]:
    """Wrap data in a standard success envelope."""
    return {"data": data, "success": True}


def error_response(code: str, message: str) -> dict[str, Any]:
    """Produce the standardised error envelope."""
    return {"error": {"code": code, "message": message}}


def paginated_response(
    items: list[Any],
    total: int,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """Wrap a paginated list in a standard envelope."""
    return {
        "data": items,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(items) < total,
        },
        "success": True,
    }
