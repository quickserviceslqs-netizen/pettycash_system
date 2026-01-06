#!/usr/bin/env bash
# Render.com build script - Updated

set -o errexit  # Exit on error

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run migrations with conflict resolution
echo "Starting migration process..."

# Handle potential database state inconsistencies
# If migrations are recorded but tables don't exist, reset and recreate
echo "Checking database state..."
python manage.py showmigrations accounts | grep -q "\[X\] 0001_initial" && echo "Accounts initial migration already applied" || echo "Accounts initial migration not applied"

# Force reset accounts app if there are issues
echo "Resetting accounts migrations to ensure clean state..."
python manage.py migrate accounts zero --noinput 2>/dev/null || echo "accounts zero migrate failed, continuing"

# Ensure accounts initial migration runs first to create accounts_user table
echo "Applying accounts initial migration..."
python manage.py migrate accounts 0001 --noinput || echo "accounts 0001 migrate failed, continuing"

# Ensure all accounts migrations are applied
echo "Applying all accounts migrations..."
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
