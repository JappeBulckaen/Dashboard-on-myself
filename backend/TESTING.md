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

Health and request-validation tests do not need a database. KPI integration tests require `TEST_DATABASE_URL` to point to a separate, empty, disposable PostgreSQL database. Add it to your local `.env` file using the commented example in `.env.example`; the VS Code test task loads that file. Do not point it at the normal application database. The test setup checks that the database identity differs from `DATABASE_URL`, creates missing tables, and wraps each test in a rollback so test rows do not persist.

Without `TEST_DATABASE_URL`, database integration tests are reported as skipped; the non-database tests still run. The integration tests use the real PostgreSQL schema because its UUID defaults are PostgreSQL-specific.

## Current test coverage

- Health endpoint returns the expected status.
- KPI request validation rejects missing, invalid, or out-of-range values.
- Invalid UUID path parameters return `422`.
- KPI listing, creation with and without an initial fact, and response serialization.
- KPI updates change only supplied fields and report missing records as `404`.
- KPI deletion removes the goal from the API list and reports missing records as `404`.
- KPI listing selects the latest fact for a metric.

## Next test layers

- Add opt-in test-schema isolation so integration tests can safely use the configured Neon database: create a unique schema per run, bind test sessions with SQLAlchemy `schema_translate_map`, reject the default/application schema, and drop the test schema during teardown. Until implemented, keep using a separate test database URL.
- Database constraint behavior, duplicate metric/goal handling, and rollback after failures.
- Authentication and user-data isolation when the demo account is replaced.
- Connector unit tests for source-to-fact normalization, duplicate ingestion, token refresh, and error handling.
- Sync integration tests for retries, partial failures, and `SyncRun` status.
- Frontend/API contract tests for loading, empty, success, and error states.
