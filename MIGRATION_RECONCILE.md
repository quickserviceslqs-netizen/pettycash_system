# Migration Reconciliation Plan — `treasury.0002_phase6_dashboard_models`

This document outlines a conservative, safe plan to reconcile schema differences that caused the `ProgrammingError` (missing `payment_id` referenced by FK) when applying `treasury.0002_phase6_dashboard_models` on the developer PostgreSQL DB.

Important: Always run these steps in a **staging** environment first and take a full DB backup before applying any schema changes.

1) Inspect current schema
   - Show applied migrations:
     ```powershell
     python .\manage.py showmigrations treasury
     ```
   - List columns for `treasury_payment`:
     ```powershell
     python - <<'PY'
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','pettycash_system.settings')
django.setup()
from django.db import connection
with connection.cursor() as c:
    c.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='treasury_payment';")
    print(c.fetchall())
PY
     ```

2) If primary key column is `id` (integer) and migration expects `payment_id` (UUID)
   - Option A (non-destructive, recommended): create a new nullable `payment_id` UUID column, backfill using a generated UUID or mapping, then update migration `0002` to reference `payment_id`, and finally make column primary if desired.
   - Option B (rename current PK): more invasive; only do if team agrees and downtime/backups are prepared.

3) Proposed safe migration steps (outline)
   - Create a Django migration `treasury/migrations/0003_add_payment_id.py` with a `RunPython` that:
     - Adds a new `payment_id` UUIDField (nullable) to `treasury_payment` (schema operation).
     - For existing rows, set `payment_id = uuid.uuid4()` or derive a stable UUID based on existing `id` (if desired).
     - Ensure uniqueness and add index.
   - Update `0002` references (if necessary) to reference `payment_id` or, better, keep `0002` unchanged and create a small `0003` that creates the FK targets expected by `0002` by adding the related columns for other tables (alerts, paymenttracking) and dropping/recreating FKs in a controlled manner.

4) Run migrations in a transaction and verify
   - `python manage.py migrate treasury 0003 --plan` to preview
   - `python manage.py migrate --database=default` (after backup)

5) Verification
   - Run test suite in staging: `python manage.py test --settings=staging_settings`.
   - Verify dashboards, alerts, payment flows in staging.

If you want, I can draft a conservative `0003` migration that adds `payment_id` as nullable UUID and backfills values, and a `scripts/` PowerShell to back up the DB before running it. Say "Draft migration and backup script" and I'll create the files for review (I will not run migrations on your DB).