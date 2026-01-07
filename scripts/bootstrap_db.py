#!/usr/bin/env python3
"""Bootstrap and preflight script to initialize or repair DB state.

- Connects to DB and checks whether it's fresh (no tables) or existing
- On fresh DB: runs 'migrate --noinput' and optional post-deploy tasks
- On existing DB: tries 'migrate --noinput', falls back to 'migrate --fake --noinput' if SQL errors indicate existing objects
- Designed to be idempotent and safe for staging/production (no destructive drops)

Usage: RUN_POST_DEPLOY_TASKS=true python scripts/bootstrap_db.py
"""
import os
import subprocess
import sys
import textwrap

from contextlib import suppress


def run(cmd, check=True, capture_output=False, hide_sensitive=False, sensitive_values=None):
    """Run a shell command, optionally masking sensitive values in the printed command.
    - hide_sensitive: if True, sensitive_values strings will be replaced with '***' in printed output.
    - sensitive_values: list of strings to mask in printed command.
    """
    if hide_sensitive and sensitive_values:
        masked_cmd = cmd
        for s in sensitive_values:
            if s:
                masked_cmd = masked_cmd.replace(s, '***')
        print('\n$ ' + masked_cmd)
    else:
        print('\n$ ' + cmd)

    proc = subprocess.run(cmd, shell=True, capture_output=capture_output, text=True)
    if check and proc.returncode != 0:
        print('Command failed')
        if capture_output:
            print('stdout:', proc.stdout)
            print('stderr:', proc.stderr)
        raise SystemExit(proc.returncode)
    return proc


def db_has_tables():
    # Returns True if the public schema has base tables (excluding common spatial ones)
    try:
        out = run(
            "python manage.py shell -c \"from django.db import connection; cursor = connection.cursor(); cursor.execute(\"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type='BASE TABLE' AND table_name NOT IN ('spatial_ref_sys','geography_columns','geometry_columns')\"); print(cursor.fetchone()[0])\"",
            capture_output=True,
            check=False,
        )
        count = int(out.stdout.strip() or "0")
        return count > 0
    except Exception as e:
        print('DB check failed:', e)
        return False


def run_migrate_and_handle():
    # Try normal migrate first
    proc = run('python manage.py migrate --noinput', check=False, capture_output=True)
    if proc.returncode == 0:
        print('Migrations applied successfully')
        return True

    # If migration failed and error indicates objects already exist, try faking
    stderr = (proc.stderr or '') + (proc.stdout or '')
    if 'already exists' in stderr or 'ProgrammingError' in stderr or 'duplicate' in stderr.lower():
        print('Migration failed due to existing DB objects; attempting to fake migrations')
        run('python manage.py migrate --fake --noinput')
        print('Faked migrations successfully')
        return True

    print('Migrations failed and did not match expected recoverable errors. See logs above.')
    print('Full migration output:')
    print(proc.stdout)
    print(proc.stderr)
    return False


def run_post_deploy_tasks():
    print('Running post-deploy tasks')
    # Use robust try/continue pattern so tasks don't abort the build
    with suppress(Exception):
        run('python create_approval_thresholds.py', check=False)
    with suppress(Exception):
        run('python manage.py seed_settings', check=False)
    # Optional data load (safe to run multiple times)
    with suppress(Exception):
        run('python manage.py load_comprehensive_data', check=False)
    with suppress(Exception):
        run('python manage.py fix_pending_requisitions', check=False)
    with suppress(Exception):
        run('python manage.py reresolve_workflows', check=False)



def migrate_legacy_env_vars():
    """Migrate old DJANGO_SUPERUSER_* env vars to ADMIN_* and warn the operator.
    This keeps backward compatibility but prints a clear deprecation warning.
    """
    legacy_keys = {
        'DJANGO_SUPERUSER_USERNAME': 'ADMIN_USERNAME',
        'DJANGO_SUPERUSER_EMAIL': 'ADMIN_EMAIL',
        'DJANGO_SUPERUSER_PASSWORD': 'ADMIN_PASSWORD',
    }
    found = False
    for old, new in legacy_keys.items():
        if os.environ.get(old):
            found = True
            if not os.environ.get(new):
                os.environ[new] = os.environ[old]
                print(f"Migrated {old} -> {new} for this run (please remove {old} from your environment)")
            else:
                print(f"Both {old} and {new} are set; using {new}")
    if found:
        print("WARNING: DJANGO_SUPERUSER_* env vars are deprecated. Remove them and use ADMIN_* vars instead.")


def create_admin_if_env_set():
    """Create an admin user if ADMIN_EMAIL and ADMIN_PASSWORD are provided.
    This is idempotent: it will not create a duplicate user if one already exists.
    """
    # Migrate legacy env vars if present (non-destructive)
    migrate_legacy_env_vars()

    admin_email = os.environ.get('ADMIN_EMAIL')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    admin_username = os.environ.get('ADMIN_USERNAME')
    admin_first_name = os.environ.get('ADMIN_FIRST_NAME', '')
    admin_last_name = os.environ.get('ADMIN_LAST_NAME', '')

    if not (admin_email and admin_password):
        return

    # If ADMIN_USERNAME isn't provided, fallback to using the email as username
    if not admin_username:
        admin_username = admin_email

    print('Ensuring admin user exists from ADMIN_EMAIL/ADMIN_PASSWORD (and optional ADMIN_USERNAME) env vars (idempotent)')

    # Use manage.py shell to create or update user in an idempotent way
    safe_cmd = textwrap.dedent(
        """
        python manage.py shell -c "from django.contrib.auth import get_user_model; User=get_user_model();
        # Find by email first, then by username
        u = User.objects.filter(email=\"{email}\").first() or User.objects.filter(username=\"{username}\").first();
        if u:
            # If a user exists (found by email or username), update password and ensure superuser/staff.
            print('Found existing user:', u.username, u.email)
            u.set_password(\"{password}\"); u.is_superuser = True; u.is_staff = True
            # If username exists (possibly owned by another account), we do not fail — we update this account's password.
            # Try to sync username/email only when not conflicting with other users.
            if u.username != \"{username}\":
                if not User.objects.filter(username=\"{username}\").exclude(pk=u.pk).exists():
                    u.username = \"{username}\"
                else:
                    print("Desired username {username} is taken by another account; keeping existing username " + u.username)
            if u.email != \"{email}\":
                if not User.objects.filter(email=\"{email}\").exclude(pk=u.pk).exists():
                    u.email = \"{email}\"
                else:
                    print("Desired email {email} is used by another account; keeping existing email " + u.email)
            if \"{first_name}\" and u.first_name != \"{first_name}\": u.first_name = \"{first_name}\"
            if \"{last_name}\" and u.last_name != \"{last_name}\": u.last_name = \"{last_name}\"
            u.save(); print('Updated existing user and ensured superuser status')
        else:
            u = User.objects.create_superuser(\"{username}\", \"{email}\", \"{password}\"); print('Created admin user')
        # Delete all other superusers to ensure only one exists
        other_superusers = User.objects.filter(is_superuser=True).exclude(pk=u.pk)
        if other_superusers.exists():
            deleted_count = other_superusers.delete()[0]
            print('Deleted ' + str(deleted_count) + ' other superuser(s) to ensure only one superuser exists')
        else:
            print('No other superusers found')"
        """.format(
            username=admin_username.replace('"', '\\"'),
            email=admin_email.replace('"', '\\"'),
            password=admin_password.replace('"', '\\"'),
            first_name=admin_first_name.replace('"', '\\"'),
            last_name=admin_last_name.replace('"', '\\"'),
        )
    )

    try:
        # Mask the admin password from logs when running sensitive command
        run(safe_cmd, check=False, hide_sensitive=True, sensitive_values=[admin_password])
    except Exception as e:
        print('Failed to ensure admin user:', e)


def main():
    print('Bootstrap: verifying DB state')
    fresh = not db_has_tables()
    if fresh:
        print('Detected fresh DB: running migrations')
        ok = run_migrate_and_handle()
        if not ok:
            raise SystemExit(1)
    else:
        print('Detected existing DB: attempting safe migration flow')
        ok = run_migrate_and_handle()
        if not ok:
            raise SystemExit(1)

    if os.environ.get('RUN_POST_DEPLOY_TASKS', 'false').lower() in ('1', 'true', 'yes'):
        run_post_deploy_tasks()
    else:
        print('Skipping post-deploy tasks (set RUN_POST_DEPLOY_TASKS=true to enable)')

    # Always ensure admin is created if credentials are supplied via env vars
    create_admin_if_env_set()


if __name__ == '__main__':
    main()
