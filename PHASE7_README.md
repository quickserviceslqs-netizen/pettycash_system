# Phase 7 — Finalization & Test Run README

This README collects commands and steps to finish Phase 7: run tests, reconcile migration blocker, execute UAT, and run load/security checks.

1) Verify tests (safe, in-memory sqlite)

PowerShell:
```powershell
python .\manage.py test tests.integration.test_e2e --settings=test_settings
python .\manage.py test accounts.tests --settings=test_settings
```

2) Reconcile DB migration blocker (Postgres)
- Before applying `treasury.0002_phase6_dashboard_models`, ensure `treasury_payment.payment_id` exists in your Postgres DB. Use the helper SQL and PS script in `scripts/`.

PowerShell (interactive):
```powershell
# Backup DB first (see scripts/backup_prepare_migration.ps1)
# Then run the SQL to add/seed payment_id
.\scripts\add_payment_id.ps1 -DbHost localhost -DbPort 5432 -DbName pettycash -DbUser postgres
```

Or run SQL directly via psql:
```powershell
psql -h localhost -U postgres -d pettycash -f scripts/add_payment_id.sql
```

After verifying the column exists and values are populated, run Django migrate:
```powershell
python .\manage.py migrate
```

3) Run UAT (staging)
- Take a DB snapshot and restore to a staging environment.
- Run UAT automation (adjust settings to staging):
```powershell
python scripts/run_uat.py --settings=staging_settings
```
- Review `reports/uat_report.txt` and record results in `PHASE7_UAT_SCENARIOS.md` spreadsheet.

4) Load testing (Locust)
- Install Locust: `pip install locust`
- Run against staging host:
```powershell
locust -f load_tests/locustfile.py --host=https://staging.example.com
```

5) Security checklist
- Follow `SECURITY_CHECKLIST.md` and run automated scans (OWASP ZAP), manual checks, and Sentry monitoring.

6) CI/CD
- The repo contains `.github/workflows/ci.yml` as a starting point. Add secrets (DB connection, Sentry DSN) in GitHub Actions and test the workflow.

7) Sign-off
- After successful staging tests, collect stakeholder sign-off and finalize `PHASE7_ACCEPTANCE_CRITERIA.md`.

If you want, I can now:
- Draft the SQL migration and PS script (done), or
- Draft a Django migration file (not applied) to be used if you prefer Django-managed migration — say "Draft Django migration" and I'll create `treasury/migrations/0003_add_payment_id.py` for review.
