#!/usr/bin/env bash
# Render.com build script - Updated

set -o errexit  # Exit on error

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Check if database has existing tables and handle accordingly
echo "Checking database state..."
HAS_TABLES=$(python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
try:
    cursor.execute(\"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name NOT IN ('spatial_ref_sys', 'geography_columns', 'geometry_columns')\")
    count = cursor.fetchone()[0]
    print('yes' if count > 0 else 'no')
except:
    print('no')
" 2>/dev/null || echo "no")

# Use a single bootstrap script to handle both fresh and existing DBs safely
python scripts/bootstrap_db.py || {
  echo "Bootstrap script failed — see output above for details";
  exit 1;
}

# Create superuser if DJANGO_SUPERUSER_* env vars are set
if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo "Creating superuser from environment variables..."
  python manage.py createsuperuser --noinput || echo "Superuser creation failed, continuing"
else
  echo "DJANGO_SUPERUSER_EMAIL and/or DJANGO_SUPERUSER_PASSWORD not set, skipping superuser creation"
fi

# Seed default system settings (always run, safe to execute multiple times)
echo "Seeding system settings..."
python manage.py seed_settings || echo "seed_settings failed, continuing"

# Optional post-deploy tasks (guarded to avoid running during build when DB is incomplete)
if [ "${RUN_POST_DEPLOY_TASKS:-false}" = "true" ]; then
  echo "RUN_POST_DEPLOY_TASKS=true — running post-deploy tasks"

  # Note: Create superuser manually via Django Admin or Render shell
  # python manage.py createsuperuser

  # Load comprehensive test data with all roles (safe to run multiple times)
  python manage.py load_comprehensive_data || echo "load_comprehensive_data failed, continuing"

  # Fix any pending requisitions with missing next_approver (bug fix)
  python manage.py fix_pending_requisitions || echo "fix_pending_requisitions failed, continuing"

  # Re-resolve workflows for any existing pending requisitions
  python manage.py reresolve_workflows || echo "reresolve_workflows failed, continuing"
else
  echo "Skipping post-deploy tasks (set RUN_POST_DEPLOY_TASKS=true to enable)"
fi
