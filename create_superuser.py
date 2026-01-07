#!/usr/bin/env python
"""
One-time script to create superuser
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pettycash_system.settings")
django.setup()

from accounts.models import User

# Create a new superuser from environment variables (safe & idempotent)
admin_email = os.environ.get("ADMIN_EMAIL")
admin_password = os.environ.get("ADMIN_PASSWORD")
admin_username = os.environ.get("ADMIN_USERNAME") or admin_email
admin_first_name = os.environ.get("ADMIN_FIRST_NAME", "")
admin_last_name = os.environ.get("ADMIN_LAST_NAME", "")

if not (admin_email and admin_password):
    print("ADMIN_EMAIL and ADMIN_PASSWORD are required to create a superuser. Exiting without creating one.")
    raise SystemExit(1)

# Remove any existing user with the same username to avoid conflicts
User.objects.filter(username=admin_username).exclude(email=admin_email).delete()

# If a user with same email exists, update it
existing = User.objects.filter(email=admin_email).first()
if existing:
    existing.username = admin_username
    existing.set_password(admin_password)
    existing.is_staff = True
    existing.is_superuser = True
    if admin_first_name:
        existing.first_name = admin_first_name
    if admin_last_name:
        existing.last_name = admin_last_name
    existing.save()
    print("Updated existing user to be superuser:", existing.username)
else:
    superuser = User.objects.create_superuser(
        username=admin_username,
        email=admin_email,
        password=admin_password,
        first_name=admin_first_name,
        last_name=admin_last_name,
    )
    print("Created superuser:", superuser.username)

print("Done. Ensure ADMIN_* env vars are set on your host and marked as secrets.")
