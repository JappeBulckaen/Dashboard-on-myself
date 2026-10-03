# Backend Testing

## Run the tests

Install the development dependencies from the `backend` directory:

```powershell
python -m pip install -r requirements-dev.txt
```

Then run the suite from that same directory:

```powershell
python -m pytest -q
```

The VS Code task **Run Backend Tests** runs the same command with the project's virtual environment and avoids shell quoting problems with this workspace path.

## Database safety

Health and request-validation tests do not need a database. KPI integration tests run against a disposable PostgreSQL schema created on the same configured app database for each test session. This keeps the tests realistic without requiring a second database URL.

The test bootstrap generates a unique schema name such as `test_<uuid>`, creates the app tables in that schema, binds each database session to it by using `SET LOCAL search_path`, and drops the schema again after the run finishes. This gives each run a clean, isolated dataset while still exercising the real PostgreSQL behavior and UUID defaults.

## Implementation notes and bugfixes

Two issues surfaced while wiring the test environment to the configured Neon database:

1. The configured `DATABASE_URL` used the raw `postgresql://` scheme without an explicit driver. SQLAlchemy defaulted to `psycopg2`, which was not installed in the virtual environment. The fix was to normalize the URL centrally in `app/db.py` so app code and tests both use `postgresql+psycopg://...` when required.
2. Simply setting `search_path` after a connection had already started a transaction caused SQLAlchemy to complain about an already-initialized transaction. The fix was to begin the transaction first and then issue `SET LOCAL search_path TO ...`, ensuring each test session remains bound to the disposable schema without leaking state.

These fixes are intentionally captured in the runtime code and test bootstrap so future contributors know why the schema-per-run strategy exists.

## Current test coverage

- Health endpoint returns the expected status.
- KPI request validation rejects missing, invalid, or out-of-range values.
- Invalid UUID path parameters return `422`.
- KPI listing, creation with and without an initial fact, and response serialization.
- KPI updates change only supplied fields and report missing records as `404`.
- KPI deletion removes the goal from the API list and reports missing records as `404`.
- KPI listing selects the latest fact for a metric.

## Next test layers

- Database constraint behavior, duplicate metric/goal handling, and rollback after failures.
- Authentication and user-data isolation when the demo account is replaced.
- Connector unit tests for source-to-fact normalization, duplicate ingestion, token refresh, and error handling.
- Sync integration tests for retries, partial failures, and `SyncRun` status.
- Frontend/API contract tests for loading, empty, success, and error states.

The current schema-per-run setup is the active alpha-phase strategy and is already implemented in `backend/tests/conftest.py`.
