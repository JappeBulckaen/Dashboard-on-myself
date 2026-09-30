# Dashboard on Myself

A personal KPI dashboard MVP. The frontend displays KPI values and targets; a FastAPI backend provides a PostgreSQL-backed API for managing them.

## Project Status

The frontend and backend foundations are in place. The frontend currently uses its mock API by default. The backend has KPI create, list, update, and delete routes, but the last saved development note reported that creating a KPI returned an Internal Server Error. Verify the current API behavior before treating those routes as fully working.

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
- KPI creation was previously reported to fail; verify the endpoint before documenting it as working.
- The VS Code backend tasks currently contain machine-specific paths and may need adjustment to work on another computer.