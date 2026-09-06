from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import get_settings

settings = get_settings()
raw_database_url = settings.database_url
if raw_database_url.startswith("postgresql://") and "+" not in raw_database_url.split("://", 1)[1][:10]:
    raw_database_url = raw_database_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(raw_database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
