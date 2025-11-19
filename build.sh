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

# Load test data (safe to run multiple times)
python manage.py load_test_data

# Fix any pending requisitions with missing next_approver (bug fix)
python manage.py fix_pending_requisitions
