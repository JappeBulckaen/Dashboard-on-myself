from app.db import Base, engine
from app.models import Connection, DashboardLayout, Fact, Goal, MetricCatalog, SyncRun, User


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Database schema created successfully.")
