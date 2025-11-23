#!/usr/bin/env bash
# Render.com build script - Updated

set -o errexit  # Exit on error

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run migrations with conflict resolution
# Fake all existing treasury migrations to avoid column/table conflicts
python manage.py migrate treasury 0001 --fake 2>/dev/null || true
python manage.py migrate treasury 0002 --fake 2>/dev/null || true
python manage.py migrate treasury 0003 --fake 2>/dev/null || true
python manage.py migrate treasury 0004 --fake 2>/dev/null || true
python manage.py migrate treasury 0005 --fake 2>/dev/null || true
python manage.py migrate treasury 0006 --fake 2>/dev/null || true
python manage.py migrate treasury 0007 --fake 2>/dev/null || true
python manage.py migrate treasury 0008 --fake 2>/dev/null || true

# Run all migrations (new ones will apply, existing ones are faked)
python manage.py migrate --no-input

# Create default approval thresholds (workflow app)
python create_approval_thresholds.py

# Note: Create superuser manually via Django Admin or Render shell
# python manage.py createsuperuser

# Load comprehensive test data with all roles (safe to run multiple times)
python manage.py load_comprehensive_data

# Fix any pending requisitions with missing next_approver (bug fix)
python manage.py fix_pending_requisitions

# Re-resolve workflows for any existing pending requisitions
python manage.py reresolve_workflows
