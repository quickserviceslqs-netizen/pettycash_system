#!/usr/bin/env python3
"""
Simple script to verify migration idempotency for the `treasury` app.
It:
  - Applies all migrations
  - Deletes `treasury` entries from `django_migrations` to simulate a DB with objects but missing migration records
  - Re-applies migrations (this should be a no-op with the idempotent SQL guards)

Usage: python scripts/check_migration_idempotent.py
"""
import subprocess
import sys

def run(cmd):
    print('\n$', cmd)
    proc = subprocess.run(cmd, shell=True)
    if proc.returncode != 0:
        print(f"Command failed with exit code {proc.returncode}")
        sys.exit(proc.returncode)

if __name__ == '__main__':
    print('Applying all migrations (baseline)')
    run('python manage.py migrate --noinput')

    print("Simulating missing treasury migration records")
    run("python manage.py shell -c \"from django.db import connection; cursor = connection.cursor(); cursor.execute(\\\"DELETE FROM django_migrations WHERE app='treasury'\\\"); print('Deleted treasury migration records')\"")

    print('Re-applying migrations to check idempotency')
    run('python manage.py migrate --noinput')

    print('\nMigration idempotency check completed successfully')
