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

# Ensure `accounts` migrations are applied first to create `accounts_user` table
python manage.py migrate accounts --noinput || echo "accounts migrate failed, continuing"

# Run all migrations (new ones will apply, existing ones are faked)
python manage.py migrate --no-input

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
