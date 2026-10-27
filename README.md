# Dashboard on Myself

A personal KPI dashboard MVP. The frontend displays KPI values and targets; a FastAPI backend provides a PostgreSQL-backed API for managing them.

## Project Status

The frontend and backend foundations are in place. The frontend currently uses its mock API by default, but the local integration path is now wired to the running backend for validation.

The backend's health and KPI create, list, update, and delete routes have been verified. The test suite runs against a disposable PostgreSQL schema created per run, so each test session uses a clean, isolated dataset without needing a separate `TEST_DATABASE_URL`.

The PostgreSQL URL normalization bug was also fixed: the app and tests now convert a raw `postgresql://...` URL to `postgresql+psycopg://...` when needed, which avoids the `ModuleNotFoundError: No module named 'psycopg2'` issue during engine creation.

## Planned Product Pivot: Life-Domain Overview

The product direction is to evolve this KPI dashboard into a smartphone-first overview of a person's life. The home screen will show progress rings for life domains (for example, Health & Fitness, Productivity, Finance, Relationships, and Household), with a score and year-over-year trend for each. Selecting a domain will open a separate view of its individual KPIs and habits.

The first version is planned as an installable Progressive Web App (PWA), keeping the current frontend and FastAPI/PostgreSQL backend where practical. Domain scores will be aggregated from user-defined KPIs and habits. Each KPI belongs to exactly one life domain. Domains will start from a predefined set that users can rename and reorder.

### Agreed First-Pass Scoring Rules

- Start with Health & Fitness, Productivity, Finance, Relationships, Household, and Other. Each KPI belongs to exactly one domain.
- Keep both numeric KPIs and yes/no habits in KPI CRUD. A numeric KPI is scored against its positive target: higher-is-better uses `value / target`; lower-is-better uses `target / value` (a zero value is 100%). Clamp either result to 100%.
- A habit score is yes check-ins divided by the expected weekdays in the calendar month. Each habit can have its own selected weekdays, and an unanswered expected day counts as no.
- A domain score is the equal-weight average of the available KPI percentages. Numeric KPIs without a recorded value are excluded; if no KPI has a score, show no score.
- Compare the last completed calendar month with the preceding completed month for MoM, and with the matching month one year earlier for YoY. Show the difference in percentage points (for example, 53% to 65% is +12 pp).

The initial implementation slice adds life domains, requires a domain and progress direction when creating a numeric KPI, and preserves existing KPI CRUD. Existing KPIs are migrated to Other so they can be reassigned instead of being classified by guesswork. The domain API supports renaming and reordering domains and returns numeric KPI scores for the last completed month with MoM/YoY trends. Habit schedules/check-ins and the overview rings remain subsequent work.

### Pivot Plan

1. Agree on the initial domain list and define how domain progress and year-over-year change are calculated, including lower-is-better KPIs and missing data.
2. Add a user-owned life-domain model. Keep the existing `User`, `MetricCatalog`, `Fact`, `Goal`, and dashboard layout models where they remain useful.
3. Add a `domain_id` foreign key to `Goal`, the user-specific KPI/goal record, so each KPI has one domain assignment. Do not put this assignment on `MetricCatalog`, since a metric definition can be reused and domain ownership is per user's KPI.
4. Introduce versioned database migrations and migrate existing KPIs into appropriate domains, with a safe fallback for unclassified records.
5. Keep KPI create, read, update, and delete (CRUD) functionality. Extend KPI creation and updates to accept a domain, and include domain information in KPI responses.
6. Add API support for listing, renaming, and reordering a user's predefined domains, plus a domain-summary response containing its score, trend, and associated KPIs.
7. Change the home screen from individual KPI cards to one progress ring per life domain. Put individual KPI/habit management and history on the domain's separate page.
8. Make the current frontend mobile-first and PWA-installable, including manifest, service worker, and appropriate mobile navigation and offline/error states.
9. Add yes/no habit check-ins as timestamped records so answers can support history and progress calculations. Add push subscriptions and reminders after the core PWA and authenticated user flows are in place.
10. Expand backend and frontend tests for domain assignment, score aggregation, trends, check-in history, user-data isolation, and the new mobile flows; pilot with sample data before relying on migrated real data.

The existing PostgreSQL setup, FastAPI service, SQLAlchemy models, KPI CRUD, facts, and goals are intended to be retained and evolved rather than replaced. The current shared demo account must be replaced with authenticated, user-isolated access before storing real personal data. Push notifications also require a secure deployed origin.

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
- `backend/alembic/`: Versioned database migrations.
- `backend/tests/`, `backend/TESTING.md`: Backend regression tests and test instructions.
- `backend/requirements-dev.txt`: Development-only test dependencies.
- `backend/create_schema.py`: Initializes a new schema or applies pending migrations.
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

Create the database schema or apply pending migrations from the `backend` directory:

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
| `GET` | `/api/domains` | List the demo user's life domains in display order. |
| `PATCH` | `/api/domains/{domain_id}` | Rename a life domain. |
| `PUT` | `/api/domains/order` | Set the complete life-domain order using domain IDs. |
| `GET` | `/api/domains/{domain_id}/summary` | Return the domain's last-completed-month score, MoM/YoY changes, and KPIs. |
| `GET` | `/api/kpis` | List KPIs for the demo user. |
| `POST` | `/api/kpis` | Create a KPI. |
| `PUT` | `/api/kpis/{kpi_id}` | Update a KPI's name, target, domain, direction, or unit. |
| `DELETE` | `/api/kpis/{kpi_id}` | Delete a KPI. |

A KPI response contains `id`, `metric_type`, `name`, `domain_id`, `domain_name`, `direction`, `value`, `has_value`, `target`, and `unit`. `has_value` distinguishes an actual zero reading from a KPI with no recorded value yet. The create request requires `name`, `target`, and `domain_id`; `direction` defaults to `at_least` and may be `at_most`. `unit`, `value`, and `metric_type` are optional.

The domain summary selects the latest fact for each KPI within each completed UTC calendar month. It averages scored KPIs equally, excludes KPIs with no fact in that month, and reports the score change in percentage points. Numeric progress is capped at 100%; a zero value for an `at_most` KPI scores 100%. The summary currently covers numeric KPIs only; habit check-ins are not implemented yet.

## Data Model

The database models cover users, life domains, metric definitions, recorded facts, goals, dashboard layouts, external connections, and sync runs. Each goal/KPI references one life domain and stores its progress direction. The current KPI routes use a demo user; authentication and external data synchronization are not implemented as user-facing flows yet.

## Known Limitations

- The frontend uses mock data unless `API_BASE` is configured.
- The backend currently uses a demo user rather than authenticated accounts.
- The VS Code backend tasks currently contain machine-specific paths and may need adjustment to work on another computer.