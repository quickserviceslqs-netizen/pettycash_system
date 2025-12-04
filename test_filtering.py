#!/usr/bin/env python
"""Test script to debug filtering"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
django.setup()

from settings_manager.models import SystemSetting

# Test: filter by email category
print("=== Testing Email Category Filter ===")
email_settings = SystemSetting.objects.filter(category='email', is_active=True).order_by('display_name')
print(f"Email settings found: {email_settings.count()}")
for s in email_settings:
    print(f"  - {s.display_name} ({s.key})")

# Test: check all categories exist
print("\n=== All Categories ===")
categories = SystemSetting.CATEGORY_CHOICES
for key, name in categories:
    count = SystemSetting.objects.filter(category=key, is_active=True).count()
    print(f"{key:15} ({name:30}): {count} settings")
