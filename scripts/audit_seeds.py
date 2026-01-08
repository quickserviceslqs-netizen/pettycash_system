#!/usr/bin/env python3
"""Audit which seeds are present and report missing ones.

This script is safe to run in production; it only reads the DB and prints
what seed data is missing and what to run to fix it.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pettycash_system.settings")
django.setup()

from workflow.models import ApprovalThreshold
from settings_manager.models import SystemSetting
from django.contrib.auth import get_user_model


def main():
    print("SEED AUDIT: Starting audit of essential seed data")

    # Approval thresholds
    at_count = ApprovalThreshold.objects.count()
    print(f"SEED AUDIT: ApprovalThreshold count: {at_count}")

    # System settings checks
    settings_count = SystemSetting.objects.count()
    print(f"SEED AUDIT: SystemSetting count: {settings_count}")

    required_keys = ["CURRENCY_CODE", "APP_VERSION"]
    missing_settings = [k for k in required_keys if not SystemSetting.objects.filter(key=k).exists()]
    if missing_settings:
        print("SEED AUDIT: Missing SystemSetting keys:")
        for k in missing_settings:
            print(f" - {k}")

    # Superuser check
    User = get_user_model()
    superusers = list(User.objects.filter(is_superuser=True).values_list("username", "email"))
    print(f"SEED AUDIT: Superusers found: {superusers}")

    # Summary
    issues = []
    if at_count == 0:
        issues.append("Approval thresholds missing; run: python create_approval_thresholds.py")
    if missing_settings:
        issues.append("System settings missing; run: python manage.py seed_settings")

    if issues:
        print("SEED AUDIT: ACTION REQUIRED — the following items are missing:")
        for i in issues:
            print(" -", i)
        print("SEED AUDIT: You can enable RUN_POST_DEPLOY_TASKS=true to run seeders automatically on next deploy, or run the commands manually.")
    else:
        print("SEED AUDIT: All essential seeds present. No action required.")


if __name__ == "__main__":
    main()
