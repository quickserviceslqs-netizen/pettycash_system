#!/usr/bin/env python
"""
One-time script to create superuser
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pettycash_system.settings")
django.setup()

from accounts.models import User

print("create_superuser.py is deprecated.")
print("Set ADMIN_EMAIL and ADMIN_PASSWORD in your environment and run scripts/bootstrap_db.py instead.")
print("This script will exit without making changes.")
raise SystemExit(0)
