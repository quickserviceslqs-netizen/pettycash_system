#!/usr/bin/env bash
# Render.com build script - Updated

set -o errexit  # Exit on error

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run migrations with conflict resolution
# Fake treasury migrations if tables already exist (production migration fix)
python manage.py migrate treasury 0002 --fake 2>/dev/null || true
python manage.py migrate treasury 0003 --fake 2>/dev/null || true
python manage.py migrate treasury --fake-initial --no-input 2>/dev/null || true

# Run all other migrations normally
python manage.py migrate --no-input

# Create superuser (one-time, safe to run multiple times)
python create_superuser.py

# Load comprehensive test data with all roles (safe to run multiple times)
python manage.py load_comprehensive_data

# Fix any pending requisitions with missing next_approver (bug fix)
python manage.py fix_pending_requisitions

# Re-resolve workflows for any existing pending requisitions
python manage.py reresolve_workflows
