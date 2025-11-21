#!/usr/bin/env bash
# Render.com build script - Updated

set -o errexit  # Exit on error

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate --no-input

# Create superuser (one-time, safe to run multiple times)
python create_superuser.py

# Load comprehensive test data with all roles (safe to run multiple times)
python manage.py load_comprehensive_data

# Fix any pending requisitions with missing next_approver (bug fix)
python manage.py fix_pending_requisitions

# Re-resolve workflows for any existing pending requisitions
python manage.py reresolve_workflows
