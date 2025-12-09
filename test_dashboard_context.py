#!/usr/bin/env python
"""Test script to debug dashboard context"""
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pettycash_system.settings")
django.setup()

from django.test import RequestFactory
from settings_manager.views import settings_dashboard
from django.contrib.auth.models import User, Group
from accounts.models import User as CustomUser

# Create a mock request
factory = RequestFactory()
request = factory.get("/settings/")

# Create a test user with admin permission
try:
    admin_user = CustomUser.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("No superuser found!")
        sys.exit(1)
    request.user = admin_user
except Exception as e:
    print(f"Error getting admin user: {e}")
    sys.exit(1)

# Mock the log_activity function to avoid issues
import settings_manager.views as views_module

original_log = views_module.log_activity
views_module.log_activity = lambda *args, **kwargs: None

try:
    # Call the view function directly to get context
    from django.http import HttpResponse
    from django.template.response import TemplateResponse

    # We need to extract the context somehow
    # Let's just check what the view builds
    from settings_manager.models import SystemSetting

    # Test without filter
    print("=== Testing WITHOUT category filter ===")
    categories = SystemSetting.CATEGORY_CHOICES
    settings_by_category = {}
    category_counts = {}

    for category_key, category_name in categories:
        all_settings = SystemSetting.objects.filter(
            category=category_key, is_active=True
        ).order_by("display_name")
        if all_settings.exists():
            category_counts[category_key] = all_settings.count()
            settings_by_category[category_name] = all_settings

    print(f"Categories found: {len(settings_by_category)}")
    print(
        f"Settings by category: {[(k, len(list(v))) for k, v in settings_by_category.items()]}"
    )
    print(f"Category counts: {category_counts}")

    # Test with filter
    print("\n=== Testing WITH category filter (email) ===")
    settings_by_category = {}
    category_counts = {}
    category_filter = "email"

    for category_key, category_name in categories:
        if category_key == category_filter:
            all_settings = SystemSetting.objects.filter(
                category=category_key, is_active=True
            ).order_by("display_name")
            if all_settings.exists():
                category_counts[category_key] = all_settings.count()
                settings_by_category[category_name] = all_settings

    print(f"Categories found: {len(settings_by_category)}")
    print(
        f"Settings by category: {[(k, len(list(v))) for k, v in settings_by_category.items()]}"
    )
    print(f"Category counts: {category_counts}")

finally:
    views_module.log_activity = original_log

print("\nContext debug complete!")
