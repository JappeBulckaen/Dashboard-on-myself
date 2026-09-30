"""Check that database settings load and the configured database is reachable."""

import os

from sqlalchemy import text

from app.config import get_settings
from app.db import engine

s = get_settings()
# Print only basic configuration checks; do not expose the connection string itself.
print("DB_SET", bool(s.database_url))
print("DB_URL_OK", s.database_url.startswith("postgresql://"))

with engine.connect() as conn:
    print("DB_TEST", conn.execute(text("SELECT 1")).scalar())
