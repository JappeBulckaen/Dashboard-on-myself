"""Create all database tables declared by the SQLAlchemy models."""

from app.db import Base, engine
# Import models so their tables are registered on Base.metadata before create_all runs.
from app.models import Connection, DashboardLayout, Fact, Goal, MetricCatalog, SyncRun, User


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Database schema created successfully.")
