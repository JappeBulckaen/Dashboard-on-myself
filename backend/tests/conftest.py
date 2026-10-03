import uuid
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import Base, get_db, normalize_database_url
from app.main import app


def generate_test_schema_name() -> str:
    """Generate a unique schema name for one test run."""
    return f"test_{uuid.uuid4().hex}"


def bind_metadata_to_schema(schema_name: str) -> dict:
    """Temporarily point all mapped tables at the current test schema."""
    original_schemas = {table: table.schema for table in Base.metadata.sorted_tables}
    for table in Base.metadata.sorted_tables:
        table.schema = schema_name
    return original_schemas


def restore_metadata_schema(original_schemas: dict) -> None:
    """Restore each mapped table to its original schema configuration."""
    for table, schema_name in original_schemas.items():
        table.schema = schema_name


def create_test_schema(engine, schema_name: str) -> None:
    """Create a disposable PostgreSQL schema and bootstrap tables into it.

    We intentionally bind the mapped metadata to the test schema before creating tables;
    this ensures the schema is used for every object created by the app and avoids the
    common leak where tables remain in the default `public` schema during test runs.
    """
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
        connection.execute(text(f'SET search_path TO "{schema_name}", public'))
        Base.metadata.create_all(bind=connection)


def drop_test_schema(engine, schema_name: str) -> None:
    """Remove the disposable schema and everything inside it."""
    with engine.begin() as connection:
        connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))


@pytest.fixture(scope="session")
def test_schema_name() -> str:
    return generate_test_schema_name()


@pytest.fixture(scope="session")
def test_engine(test_schema_name: str):
    database_url = normalize_database_url(get_settings().database_url)
    engine = create_engine(database_url, pool_pre_ping=True)
    original_schemas = bind_metadata_to_schema(test_schema_name)
    try:
        create_test_schema(engine, test_schema_name)
        yield engine
    finally:
        drop_test_schema(engine, test_schema_name)
        restore_metadata_schema(original_schemas)
        engine.dispose()


@pytest.fixture
def db_session(test_engine, test_schema_name: str) -> Iterator[Session]:
    # The transaction must begin before we set the schema path for the session.
    # If the search path is changed after SQLAlchemy has already started a transaction,
    # Postgres raises an InvalidRequestError. This fixture keeps each test bound to the
    # run-specific schema while still rolling the session back cleanly at teardown.
    connection = test_engine.connect()
    transaction = connection.begin()
    connection.execute(text(f'SET LOCAL search_path TO "{test_schema_name}", public'))
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def api_client(db_session: Session) -> Iterator[TestClient]:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
