# Weather Backend

A complete **Weather Application Backend** built with FastAPI, PostgreSQL, and MVC architecture.  
Built for the **PM Accelerator AI Engineer Intern** technical assessment.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Technologies](#3-technologies)
4. [Prerequisites](#4-prerequisites)
5. [Virtual Environment Setup](#5-virtual-environment-setup)
6. [Dependency Installation](#6-dependency-installation)
7. [Environment Configuration](#7-environment-configuration)
8. [Database Setup and Migrations](#8-database-setup-and-migrations)
9. [Running the Application](#9-running-the-application)
10. [API Endpoints](#10-api-endpoints)
11. [Error Handling and Validation](#11-error-handling-and-validation)
12. [Export Functionality](#12-export-functionality)
13. [Running Tests and Ruff](#13-running-tests-and-ruff)
14. [Swagger Documentation](#14-swagger-documentation)
15. [Known Weather Provider Limitations](#15-known-weather-provider-limitations)
16. [About PM Accelerator](#16-about-pm-accelerator)

---

## 1. Project Overview

This backend demonstrates:

- **REST API development** with FastAPI
- **MVC-inspired architecture** with clear separation of concerns
- **External API integration** — Open-Meteo Geocoding and Weather APIs (no API key required)
- **PostgreSQL persistence** via SQLAlchemy 2.0 (async)
- **Full CRUD operations** on saved weather records
- **Input validation** using Pydantic v2
- **Centralised error handling** with consistent JSON error responses
- **Data export** in JSON and CSV formats
- **Database migrations** managed by Alembic
- **Automated tests** with pytest (mocked external APIs, in-memory SQLite)

---

## 2. Architecture

The project uses an MVC-inspired architecture adapted to FastAPI conventions.

```text
weather-backend/
├── src/
│   ├── assets/         # Static metadata: WMO weather-code descriptions
│   ├── controllers/    # Request coordination — orchestrates stores + external clients
│   ├── helpers/        # Config, DB engine, HTTP clients, logging, exceptions, export utilities
│   ├── models/         # SQLAlchemy ORM models (WeatherRecord)
│   ├── routes/         # FastAPI router definitions and endpoint declarations
│   ├── schemas/        # Pydantic v2 request/response schemas
│   └── stores/         # Database queries and persistence (CRUD layer)
├── tests/              # Automated test suite
├── migrations/         # Alembic environment and version scripts
├── main.py             # Application entry point
├── alembic.ini
├── pyproject.toml
├── requirements.txt
├── .env.example
└── README.md
```

### Folder responsibilities

| Folder | Role |
|---|---|
| `src/models/` | SQLAlchemy declarative models. Defines schema; no business logic. |
| `src/schemas/` | Pydantic v2 models for request validation and response serialisation. |
| `src/stores/` | All database queries. One store class per model. Controllers call stores; routes never touch the DB directly. |
| `src/controllers/` | Coordinates one request: validates inputs, calls the weather client, calls the store, and returns a result. Thin — no SQL, no HTTP. |
| `src/routes/` | FastAPI `APIRouter` instances. Maps HTTP verbs/paths to controller calls. No business logic. |
| `src/helpers/` | Cross-cutting concerns: settings, async DB engine, HTTPX weather/geocoding client, logging, typed exceptions, response builders, and export utilities. |
| `src/assets/` | Static files: WMO weather-code-to-description mapping (`wmo_codes.json`). |

---

## 3. Technologies

| Technology | Version | Purpose |
|---|---|---|
| Python | 3.12+ | Language |
| FastAPI | 0.115 | Web framework |
| Uvicorn | 0.32 | ASGI server |
| SQLAlchemy | 2.0 | Async ORM |
| psycopg (v3) | 3.2 | PostgreSQL async driver |
| Alembic | 1.14 | Database migrations |
| Pydantic | 2.10 | Validation and serialisation |
| pydantic-settings | 2.6 | Environment-based configuration |
| HTTPX | 0.28 | Async HTTP client (Open-Meteo) |
| pytest + pytest-asyncio | 8.x / 0.24 | Automated tests |
| Ruff | 0.8 | Linting and formatting |
| aiosqlite | — | In-memory SQLite for tests (no PostgreSQL required to run tests) |

---

## 4. Prerequisites

### Python 3.12+

Download from [python.org](https://www.python.org/downloads/) and install with **"Add to PATH"** checked.

### PostgreSQL

1. Download PostgreSQL 16 from [postgresql.org](https://www.postgresql.org/download/).
2. Install with the default settings (port `5432`, user `postgres`).
3. Create the application database:

```sql
-- In psql or pgAdmin:
CREATE DATABASE weather_db;
```

Or using the CLI:

```bash
psql -U postgres -c "CREATE DATABASE weather_db;"
```

---

## 5. Virtual Environment Setup

```bash
# Create
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (macOS / Linux)
source .venv/bin/activate
```

---

## 6. Dependency Installation

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Tests only** also require `aiosqlite` (not in `requirements.txt` because it is not a production dependency):
> ```bash
> pip install aiosqlite
> ```

---

## 7. Environment Configuration

Copy `.env.example` to `.env` and edit it:

```bash
cp .env.example .env
```

```dotenv
APP_NAME=Weather Backend
APP_ENV=development
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/weather_db
CORS_ORIGINS=http://localhost:5500,http://127.0.0.1:5500
HTTP_TIMEOUT_SECONDS=10
LOG_LEVEL=INFO
```

| Variable | Description |
|---|---|
| `APP_NAME` | Application display name |
| `APP_ENV` | `development` or `production` |
| `DATABASE_URL` | SQLAlchemy async connection URL (use `postgresql+psycopg://`) |
| `CORS_ORIGINS` | Comma-separated list of allowed CORS origins |
| `HTTP_TIMEOUT_SECONDS` | Timeout for Open-Meteo HTTP requests (default `10`) |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` (default `INFO`) |

---

## 8. Database Setup and Migrations

### Apply migrations

```bash
alembic upgrade head
```

### Create a new migration after changing a model

```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

### Roll back one migration

```bash
alembic downgrade -1
```

---

## 9. Running the Application

```bash
uvicorn main:app --reload
```

The application starts at **http://localhost:8000**.

---

## 10. API Endpoints

All endpoints are prefixed with `/api/v1`.

### A. Search and Save Weather

```
POST /api/v1/weather/search
```

**By location name:**
```json
{
  "location": "Mansoura, Egypt",
  "start_date": "2026-10-16",
  "end_date": "2026-10-20"
}
```

**By coordinates:**
```json
{
  "latitude": 31.0364,
  "longitude": 31.3807,
  "start_date": "2026-10-16",
  "end_date": "2026-10-20"
}
```

Returns `201 Created` with the persisted record including normalized weather data.

---

### B. Current Weather

```
GET /api/v1/weather/current?location=Mansoura
GET /api/v1/weather/current?latitude=31.0364&longitude=31.3807
```

---

### C. Forecast

```
GET /api/v1/weather/forecast?location=Mansoura&days=5
GET /api/v1/weather/forecast?latitude=31.0364&longitude=31.3807&days=7
```

`days` must be between 1 and 16.

---

### D. History – List

```
GET /api/v1/weather/history
GET /api/v1/weather/history?limit=10&offset=0&location=Mansoura&start_date=2026-10-01
```

### D. History – Single Record

```
GET /api/v1/weather/history/{record_id}
```

---

### E. Update History

```
PUT /api/v1/weather/history/{record_id}
```

```json
{
  "location": "Cairo, Egypt",
  "start_date": "2026-10-10",
  "end_date": "2026-10-15"
}
```

Automatically re-fetches weather data if location or dates change.

---

### F. Delete History

```
DELETE /api/v1/weather/history/{record_id}
```

Returns `204 No Content` on success.

---

### G. Data Export

```
GET /api/v1/exports/weather?format=json
GET /api/v1/exports/weather?format=csv
GET /api/v1/exports/weather?format=csv&location=Mansoura&start_date=2026-10-01
```

Returns a downloadable file attachment.

---

### H. Health Check

```
GET /health          # Liveness
GET /health/ready    # Readiness (checks DB connectivity)
```

---

## 11. Error Handling and Validation

All errors use a consistent JSON structure:

```json
{
  "error": {
    "code": "LOCATION_NOT_FOUND",
    "message": "The location 'XyzCity' could not be found."
  }
}
```

| HTTP Status | Error Code | Cause |
|---|---|---|
| `400` | `INVALID_DATE_RANGE` | start_date > end_date, or range too large |
| `400` | `INVALID_COORDINATES` | Coordinates provided without both lat and lon |
| `400` | `UNSUPPORTED_EXPORT_FORMAT` | format= is not json or csv |
| `400` | `VALIDATION_ERROR` | Service-level validation failure |
| `404` | `LOCATION_NOT_FOUND` | Geocoding returned no results |
| `404` | `RECORD_NOT_FOUND` | No record with the given ID |
| `422` | `VALIDATION_ERROR` | Pydantic request schema validation failure |
| `500` | `INTERNAL_ERROR` | Unexpected server error |
| `502` | `EXTERNAL_API_ERROR` | Open-Meteo returned a non-200 response |
| `503` | `SERVICE_UNAVAILABLE` | Temporary service unavailability |
| `504` | `EXTERNAL_API_TIMEOUT` | Open-Meteo did not respond in time |

Stack traces and SQL details are **never** returned to clients. Technical errors are logged server-side only.

---

## 12. Export Functionality

`GET /api/v1/exports/weather?format=json|csv`

- **JSON**: Returns a JSON array of all matching records, with a timestamped filename attachment.
- **CSV**: Returns a CSV file with one row per record. The `weather_data` column contains JSON-encoded weather data. Values that start with `=`, `+`, `-`, or `@` are prefixed with a single-quote to prevent spreadsheet formula injection.
- Optional filters: `location`, `start_date`, `end_date`.
- The response includes `Content-Disposition: attachment; filename="weather_export_<timestamp>.json"`.

---

## 13. Running Tests and Ruff

### Tests

Tests use an **in-memory SQLite database** and **mock all external HTTP calls** — no PostgreSQL or internet connection required.

```bash
# Install test dependency
pip install aiosqlite

# Run all tests with verbose output
pytest -v

# Run a specific test file
pytest tests/test_weather_search.py -v

# Run with coverage (if pytest-cov is installed)
pip install pytest-cov
pytest --cov=src --cov-report=term-missing
```

### Ruff (linting)

```bash
# Check
ruff check .

# Auto-fix
ruff check . --fix

# Format
ruff format .
```

---

## 14. Swagger Documentation

With the application running, open:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## 15. Known Weather Provider Limitations

| Limitation | Detail |
|---|---|
| **Archive lag** | Open-Meteo archive data has an approximate 5-day lag. Requests for very recent dates are served from the forecast API instead. |
| **Archive start** | Historical data is only available from 1940-01-01 onwards. |
| **Forecast horizon** | Open-Meteo supports a maximum of 16 days into the future. |
| **Date range cap** | This API caps the requested range at 365 days per request to prevent abuse. |
| **No API key** | Open-Meteo is a free, open API. No credentials are required. |
| **Rate limits** | Open-Meteo imposes undocumented fair-use rate limits. The client retries twice with a 1-second delay on transient errors. |

---

## 16. About PM Accelerator

**PM Accelerator** is a product management career accelerator that helps aspiring and experienced product managers land their dream roles through mentorship, community, and hands-on learning. Based on their official LinkedIn company description, PM Accelerator is dedicated to helping individuals break into and advance within product management by providing structured programs, real-world experience, and a network of industry professionals.

> *This description is based on publicly available information from PM Accelerator's LinkedIn company page.*
