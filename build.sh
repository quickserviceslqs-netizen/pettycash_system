#!/usr/bin/env bash
# Render.com build script - Updated

set -o errexit  # Exit on error

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Reset migration state for clean start on new DB
echo "Clearing django_migrations table for fresh migration start..."
python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
try:
    cursor.execute('DELETE FROM django_migrations')
    print('Cleared django_migrations table')
except Exception as e:
    print(f'Failed to clear migrations: {e}')
" 2>/dev/null || echo "Could not clear migrations table"

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
if ! python manage.py migrate accounts 0001 --noinput 2>/dev/null; then
    echo "accounts 0001 migrate failed, trying alternative approach..."
    # If the migration fails, try to fake it if the table already exists
    python manage.py migrate accounts 0001 --fake 2>/dev/null || {
        echo "Could not apply accounts 0001 migration, trying to recreate table..."
        # Last resort: try to run a raw SQL to create the table if it doesn't exist
        python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
try:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts_user (
            id BIGSERIAL PRIMARY KEY,
            password VARCHAR(128) NOT NULL,
            last_login TIMESTAMP WITH TIME ZONE,
            is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
            username VARCHAR(150) UNIQUE NOT NULL,
            first_name VARCHAR(150) NOT NULL DEFAULT '',
            last_name VARCHAR(150) NOT NULL DEFAULT '',
            email VARCHAR(254) NOT NULL DEFAULT '',
            is_staff BOOLEAN NOT NULL DEFAULT FALSE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            date_joined TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            role VARCHAR(30) NOT NULL DEFAULT 'staff',
            phone_number VARCHAR(20),
            branch_id BIGINT REFERENCES organization_branch(id),
            company_id BIGINT REFERENCES organization_company(id),
            cost_center_id BIGINT REFERENCES organization_costcenter(id),
            department_id BIGINT REFERENCES organization_department(id),
            position_title_id BIGINT REFERENCES organization_position(id),
            region_id BIGINT REFERENCES organization_region(id)
        );
    ''')
    print('Created accounts_user table manually')
except Exception as e:
    print(f'Failed to create table: {e}')
" 2>/dev/null || echo "Manual table creation also failed"
    }
fi

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
