#!/usr/bin/env python3
"""
Create or update a superuser from environment variables or command-line arguments.

Usage examples:
  # Use env vars (good for Render one-off shells)
  ADMIN_EMAIL="you@example.com" ADMIN_PASSWORD="S3cret!" python create_superuser.py

  # Or pass flags
  python create_superuser.py --email you@example.com --password S3cret!

  # Force delete all existing superusers then create (destructive)
  ADMIN_EMAIL="you@example.com" ADMIN_PASSWORD="S3cret!" python create_superuser.py --force --yes

Notes:
- This is intended as a safe, auditable one-off utility. By default it will create or update the
  admin user and then remove *other* superusers so only the target remains.
- Use `--force` only when you explicitly want to delete all superusers first (backup first!).
"""

import os
import argparse
import getpass
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pettycash_system.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()


def mask(s):
    if not s:
        return ""
    return s[:1] + "***" + s[-1:]


def parse_args():
    p = argparse.ArgumentParser(description="Create or update a superuser from env or CLI")
    p.add_argument("--email", help="Admin email (overrides ADMIN_EMAIL env var)")
    p.add_argument("--username", help="Admin username (defaults to email)")
    p.add_argument("--password", help="Admin password (overrides ADMIN_PASSWORD env var)")
    p.add_argument("--first-name", help="First name", default="")
    p.add_argument("--last-name", help="Last name", default="")
    p.add_argument(
        "--force",
        action="store_true",
        help="Delete all existing superusers first (destructive). Use --yes to skip confirmation.",
    )
    p.add_argument(
        "--yes",
        action="store_true",
        help="Automatically confirm destructive actions (use with --force)",
    )
    return p.parse_args()


def confirm(prompt):
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except Exception:
        return False


def main():
    args = parse_args()

    admin_email = args.email or os.environ.get("ADMIN_EMAIL")
    admin_password = args.password or os.environ.get("ADMIN_PASSWORD")
    admin_username = args.username or os.environ.get("ADMIN_USERNAME") or admin_email
    first_name = args.first_name or os.environ.get("ADMIN_FIRST_NAME", "")
    last_name = args.last_name or os.environ.get("ADMIN_LAST_NAME", "")
    force = args.force
    auto_yes = args.yes

    if not admin_email:
        print("ERROR: admin email not provided. Use --email or set ADMIN_EMAIL in environment.")
        raise SystemExit(1)

    if not admin_password:
        # Try to prompt for password if running interactively
        if sys.stdin.isatty():
            admin_password = getpass.getpass("Admin password: ")
        else:
            print("ERROR: admin password not provided. Use --password or set ADMIN_PASSWORD in environment.")
            raise SystemExit(1)

    print(f"Using admin email: {admin_email}")
    print(f"Using admin username: {admin_username}")
    print(f"Using admin password: {mask(admin_password)}")

    if force:
        if not auto_yes:
            print("WARNING: --force will DELETE ALL superusers. This is destructive.")
            if not confirm("Type YES to proceed: "):
                print("Aborting.")
                raise SystemExit(1)
        # Perform destructive delete
        deleted = User.objects.filter(is_superuser=True).delete()
        print(f"Deleted {deleted[0]} superuser(s)")
        # Create the new superuser
        u = User.objects.create_superuser(admin_username, admin_email, admin_password)
        if first_name:
            u.first_name = first_name
        if last_name:
            u.last_name = last_name
        u.save()
        print(f"Created admin user (force): {u.username}")
        return

    # Non-force: find by email or username, update/create and then remove other superusers
    u = User.objects.filter(email=admin_email).first() or User.objects.filter(username=admin_username).first()
    if u:
        print(f"Found existing user: {u.username} ({u.email}) — updating password and promoting to superuser")
        u.set_password(admin_password)
        u.is_superuser = True
        u.is_staff = True
        # Try to sync username/email when not conflicting
        if u.username != admin_username:
            if not User.objects.filter(username=admin_username).exclude(pk=u.pk).exists():
                u.username = admin_username
            else:
                print(f"Desired username {admin_username} is taken by another account; keeping existing username {u.username}")
        if u.email != admin_email:
            if not User.objects.filter(email=admin_email).exclude(pk=u.pk).exists():
                u.email = admin_email
            else:
                print(f"Desired email {admin_email} is used by another account; keeping existing email {u.email}")
        if first_name and u.first_name != first_name:
            u.first_name = first_name
        if last_name and u.last_name != last_name:
            u.last_name = last_name
        u.save()
        print("Updated existing user and ensured superuser status")
    else:
        # Create new superuser
        u = User.objects.create_superuser(admin_username, admin_email, admin_password)
        if first_name:
            u.first_name = first_name
        if last_name:
            u.last_name = last_name
        u.save()
        print("Created admin user")

    # Delete all other superusers to ensure only one remains
    other_superusers = User.objects.filter(is_superuser=True).exclude(pk=u.pk)
    if other_superusers.exists():
        deleted_count = other_superusers.delete()[0]
        print(f"Deleted {deleted_count} other superuser(s) to ensure only one superuser exists")
    else:
        print("No other superusers found")


if __name__ == "__main__":
    main()
