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

if [ "$HAS_TABLES" = "yes" ]; then
    echo "Database has existing tables, faking all migrations to avoid conflicts..."
    python manage.py migrate --fake --no-input
else
    echo "Database is clean, running migrations normally..."
    python manage.py migrate --no-input
fi

# Optional post-deploy tasks (guarded to avoid running during build when DB is incomplete)
if [ "${RUN_POST_DEPLOY_TASKS:-false}" = "true" ]; then
  echo "RUN_POST_DEPLOY_TASKS=true — running post-deploy tasks"
  # Create default approval thresholds (workflow app)
  python create_approval_thresholds.py || echo "create_approval_thresholds.py failed, continuing"

  # Seed default system settings (settings_manager app)
  python manage.py seed_settings || echo "seed_settings failed, continuing"

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
