# Weather App (FastAPI + Vanilla JS)

A full-stack weather application built with a **FastAPI** backend, Open-Meteo integration, and a **Vanilla JS** frontend.

---

## Quick Start (How to Run)

### 1. Prerequisites
- **Python 3.10+**
- *(Optional)* PostgreSQL (only needed for persisting search history; current weather and forecast work without it)

---

### 2. Setup Virtual Environment & Install Dependencies

Open your terminal in the project root directory:

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### 3. Environment Configuration (Optional)

Copy `.env.example` to `.env`:

**Windows:**
```powershell
copy .env.example .env
```

**macOS / Linux:**
```bash
cp .env.example .env
```

> **Note:** The app will run out of the box with defaults. Current weather and multi-day forecasts do not require a database connection.

---

### 4. Run the Server

Start the development server with Uvicorn:

```bash
uvicorn main:app --reload
```

---

### 5. Access the App

- **Web UI:** Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.
- **Interactive API Docs (Swagger):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Running Automated Tests

Run the test suite using pytest:

```bash
pytest
```

---

## (Optional) Setting Up PostgreSQL for Search History

If you want to use the database features (saving searches to history, export to CSV/JSON):

1. Ensure PostgreSQL is running and create a database (e.g. `weather_db`).
2. Update `DATABASE_URL` in `.env`:
   ```env
   DATABASE_URL=postgresql+psycopg://<username>:<password>@localhost:5432/weather_db
   ```
3. Run database migrations:
   ```bash
   alembic upgrade head
   ```