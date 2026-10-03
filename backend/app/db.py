from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import get_settings


def normalize_database_url(raw_database_url: str) -> str:
    """Select the psycopg driver when the configured PostgreSQL URL omits one.

    Root cause: the project uses a raw PostgreSQL URL without an explicit driver.
    SQLAlchemy defaults to psycopg2, but this environment only has psycopg installed,
    which raises a ModuleNotFoundError during engine creation. The normalization keeps
    app code and tests aligned with the actual runtime dependency.
    """
    if raw_database_url.startswith("postgresql://") and "+" not in raw_database_url.split("://", 1)[1][:10]:
        return raw_database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return raw_database_url


settings = get_settings()
raw_database_url = normalize_database_url(settings.database_url)
engine = create_engine(raw_database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Yield a database session and close it after the caller finishes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
