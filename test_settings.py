"""
Test settings for running Phase 4 tests with SQLite.
"""

from pettycash_system.settings import *

# Use DATABASE_URL (Postgres) in CI when available, otherwise fall back to an in-memory SQLite DB
import os
import dj_database_url

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600),
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",  # Use in-memory SQLite for fast tests
        }
    }
