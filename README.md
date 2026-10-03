# Dashboard on Myself

A personal KPI dashboard MVP. The frontend displays KPI values and targets; a FastAPI backend provides a PostgreSQL-backed API for managing them.

## Project Status

The frontend and backend foundations are in place. The frontend currently uses its mock API by default, but the local integration path is now wired to the running backend for validation.

The backend's health and KPI create, list, update, and delete routes have been verified. The test suite runs against a disposable PostgreSQL schema created per run, so each test session uses a clean, isolated dataset without needing a separate `TEST_DATABASE_URL`.

The PostgreSQL URL normalization bug was also fixed: the app and tests now convert a raw `postgresql://...` URL to `postgresql+psycopg://...` when needed, which avoids the `ModuleNotFoundError: No module named 'psycopg2'` issue during engine creation.

## Project Structure

- `dashboard-mvp.html`, `style.css`: Dashboard page and styling.
- `js/api.js`: API client and in-memory mock API.
- `js/state.js`: Frontend KPI state.
- `js/render.js`: KPI loading and rendering.
- `js/modal.js`: KPI form and modal interactions.
- `js/main.js`: Page initialization.
- `backend/app/main.py`: FastAPI routes and request/response models.
- `backend/app/models.py`: SQLAlchemy database models.
- `backend/app/db.py`, `backend/app/config.py`: Database connection and settings.
- `backend/tests/`, `backend/TESTING.md`: Backend regression tests and test instructions.
- `backend/requirements-dev.txt`: Development-only test dependencies.
- `backend/create_schema.py`: Creates database tables.
- `backend/validate_db.py`: Checks database configuration and connectivity.
- `scripts/Stop-Backend.ps1`: Stops the local Uvicorn backend process.

## Requirements

- Python 3
- A reachable PostgreSQL database
- Windows PowerShell for the commands below

## Setup

From the project root, create and activate a virtual environment and install the backend dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
```

Create a local `.env` file based on `.env.example`, then set `DATABASE_URL` to your PostgreSQL connection string. Keep credentials in `.env`; do not commit them.

Create the database tables from the `backend` directory:

```powershell
Set-Location backend
python create_schema.py
```

## Run the Application

### Backend

From the `backend` directory, with the project virtual environment active:

```powershell
python -m uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`. Check `http://127.0.0.1:8000/health` for the health endpoint and `http://127.0.0.1:8000/docs` for FastAPI's interactive API documentation.

### Frontend

Open `dashboard-mvp.html` in a browser. By default, it uses the in-memory mock API; mock data is not persisted across page reloads.

To use the FastAPI backend instead, configure `API_BASE` in `js/api.js` to point to the running API. The frontend/backend integration should be verified before relying on it.

## Testing

From the `backend` directory, install development dependencies and run the suite:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The VS Code task **Run Backend Tests** runs the suite with the project's virtual environment. See [backend/TESTING.md](backend/TESTING.md) for coverage and the separate PostgreSQL test-database requirements.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check that the API is running. |
| `GET` | `/api/kpis` | List KPIs for the demo user. |
| `POST` | `/api/kpis` | Create a KPI. |
| `PUT` | `/api/kpis/{kpi_id}` | Update a KPI's name, target, or unit. |
| `DELETE` | `/api/kpis/{kpi_id}` | Delete a KPI. |

A KPI response contains `id`, `metric_type`, `name`, `value`, `target`, and `unit`. The create request accepts `name` and `target`, with optional `unit`, `value`, and `metric_type`.

## Data Model

The database models cover users, metric definitions, recorded facts, goals, dashboard layouts, external connections, and sync runs. The current KPI routes use a demo user; authentication and external data synchronization are not implemented as user-facing flows yet.

## Known Limitations

- The frontend uses mock data unless `API_BASE` is configured.
- The backend currently uses a demo user rather than authenticated accounts.
- The VS Code backend tasks currently contain machine-specific paths and may need adjustment to work on another computer.