"""src/helpers/export.py — JSON and CSV export utilities with formula-injection protection."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any


# Characters that trigger formula injection in spreadsheet apps
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _sanitize_cell(value: Any) -> str:
    """
    Convert a value to a safe string for CSV output.
    Prepend a single-quote to values that look like spreadsheet formulas.
    """
    text = str(value) if value is not None else ""
    if text and text[0] in _FORMULA_PREFIXES:
        text = "'" + text
    return text


def records_to_json(records: list[dict[str, Any]]) -> bytes:
    """Serialise a list of record dicts to indented JSON bytes."""
    return json.dumps(records, default=str, ensure_ascii=False, indent=2).encode("utf-8")


def records_to_csv(records: list[dict[str, Any]]) -> bytes:
    """
    Serialise a list of record dicts to CSV bytes.

    The weather_data JSONB column is flattened to a JSON string so it fits
    in a single column without breaking the CSV structure.
    """
    if not records:
        return b""

    output = io.StringIO()

    fieldnames = [
        "id",
        "location_name",
        "country",
        "latitude",
        "longitude",
        "start_date",
        "end_date",
        "provider",
        "created_at",
        "updated_at",
        "weather_data",
    ]

    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames,
        extrasaction="ignore",
        quoting=csv.QUOTE_ALL,
        lineterminator="\r\n",
    )
    writer.writeheader()

    for record in records:
        row: dict[str, str] = {}
        for field in fieldnames:
            val = record.get(field)
            if isinstance(val, dict | list):
                val = json.dumps(val, default=str)
            row[field] = _sanitize_cell(val)
        writer.writerow(row)

    return output.getvalue().encode("utf-8")


def safe_export_filename(prefix: str, fmt: str) -> str:
    """Build a safe, timestamped export filename."""
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    # Strip any path separators from the prefix for safety
    safe_prefix = prefix.replace("/", "_").replace("\\", "_")
    return f"{safe_prefix}_{timestamp}.{fmt}"
