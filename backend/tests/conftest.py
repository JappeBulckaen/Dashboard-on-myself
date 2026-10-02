import os
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app import models
from app.config import get_settings
from app.db import Base, get_db
from app.main import app


@pytest.fixture(scope="session")
def test_engine():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to a separate, disposable PostgreSQL database")

    test_url = make_url(database_url)
    application_url = make_url(get_settings().database_url)
    if test_url.get_backend_name() != "postgresql":
        pytest.fail("TEST_DATABASE_URL must point to PostgreSQL")

    test_identity = (test_url.host, test_url.port, test_url.database)
    application_identity = (
        application_url.host,
        application_url.port,
        application_url.database,
    )
    if test_identity == application_identity:
        pytest.fail("TEST_DATABASE_URL must not point to the application's DATABASE_URL")

    if test_url.drivername == "postgresql":
        test_url = test_url.set(drivername="postgresql+psycopg")

    engine = create_engine(test_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine) -> Iterator[Session]:
    connection = test_engine.connect()
    transaction = connection.begin()
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
