"""
Test settings for running Phase 4 tests with SQLite.
"""

from pettycash_system.settings import *

# Override DATABASE to use SQLite for tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # Use in-memory SQLite for fast tests
    }
}


