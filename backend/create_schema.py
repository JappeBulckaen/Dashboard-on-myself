"""Initialize a new database schema or apply pending schema migrations."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.db import Base, engine
# Import models so their tables are registered on Base.metadata before create_all runs.
from app.models import CheckIn, Connection, DashboardLayout, Fact, Goal, LifeDomain, MetricCatalog, SyncRun, User


if __name__ == "__main__":
    alembic_config = Config(str(Path(__file__).resolve().parent / "alembic.ini"))
    if inspect(engine).has_table("goals"):
        command.upgrade(alembic_config, "head")
    else:
        Base.metadata.create_all(bind=engine)
        command.stamp(alembic_config, "head")
    print("Database schema created successfully.")
