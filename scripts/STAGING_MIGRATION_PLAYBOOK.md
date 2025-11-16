Staging Migration Playbook

Purpose
- Safely reconcile schema differences that prevented `treasury.0002_phase6_dashboard_models` from being applied by adding a `payment_id` UUID on `treasury_payment`, applying migrations, and running UAT.

Important notes
- Always take a full DB backup before running any schema changes.
- Prefer to run this in a staging environment first. Do not run on production without approval and a rollback plan.

Prerequisites
- `psql`/`pg_dump` available on the machine executing the steps.
- You have credentials with privileges to create extensions and alter tables.
- Working Django virtualenv with project dependencies installed.

High-level steps (safe, manual-first)
1. Take a full backup of the staging DB.
   - Example (PowerShell):

```powershell
$env:PGPASSWORD = Read-Host -AsSecureString "Enter DB password" | ConvertFrom-SecureString
# Or run interactively and set PGPASSWORD
pg_dump -h STAGING_DB_HOST -p 5432 -U STAGING_DB_USER -F c -b -v -f .\backups\staging_backup_$(Get-Date -Format yyyyMMdd_HHmmss).dump STAGING_DB_NAME
```

2. Verify backup is restorable.
   - Optionally restore to a test schema to sanity-check.

3. Add/seed `payment_id` to `treasury_payment`.
   - Option A (recommended): run the PowerShell helper which asks for password and runs the SQL helper:

```powershell
.\scripts\add_payment_id.ps1 -DbHost <STAGING_DB_HOST> -DbPort 5432 -DbName <STAGING_DB_NAME> -DbUser <STAGING_DB_USER>
```

   - Option B (manual SQL): run `psql` to execute `scripts/add_payment_id.sql`.

4. Verify column exists and is populated:

```powershell
psql -h <STAGING_DB_HOST> -U <STAGING_DB_USER> -d <STAGING_DB_NAME> -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name='treasury_payment';"
psql -h <STAGING_DB_HOST> -U <STAGING_DB_USER> -d <STAGING_DB_NAME> -c "SELECT COUNT(*) FROM treasury_payment WHERE payment_id IS NULL;"
```

5. Apply Django migrations (staging settings):

```powershell
python .\manage.py migrate --settings=staging_settings
```

6. Run UAT automation and sanity checks:

```powershell
python .\scripts\run_uat.py --settings=staging_settings
# Inspect reports/uat_report.txt
```

7. Run smoke tests manually (a few key URLs) and verify dashboards/alerts.

Rollback plan
- If the change causes unexpected issues:
  - Restore DB from the backup taken in step 1.
  - Re-deploy previous app release if necessary.

Post-migration
- Confirm `treasury.0002_phase6_dashboard_models` is applied and no migration errors remain.
- Run load tests and security scans before stakeholder sign-off.

Contact
- If you want, provide CI job access or invite me to run these steps interactively; otherwise, run the scripted helper locally and report results.
