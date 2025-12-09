"""
Export production users to local database
Run this script on Render to export user data, then import locally
"""

import json
import os
from datetime import datetime

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pettycash_system.settings")
django.setup()

from django.contrib.auth import get_user_model

from accounts.models import App

User = get_user_model()

print("Exporting production users...")
print("=" * 80)

users_data = []

for user in User.objects.all():
    # Get app assignments
    apps = list(user.assigned_apps.values_list("name", flat=True))

    # Get permissions
    perms = []
    for perm in user.user_permissions.all():
        perms.append(
            {"app_label": perm.content_type.app_label, "codename": perm.codename}
        )

    # Get groups
    groups = list(user.groups.values_list("name", flat=True))

    user_dict = {
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_superuser": user.is_superuser,
        "is_staff": user.is_staff,
        "is_active": user.is_active,
        "role": user.role,
        "assigned_apps": apps,
        "permissions": perms,
        "groups": groups,
        "date_joined": user.date_joined.isoformat() if user.date_joined else None,
    }

    users_data.append(user_dict)

    print(f"\n✓ Exported: {user.username}")
    print(f"  Email: {user.email}")
    print(f"  Superuser: {user.is_superuser}")
    print(f"  Role: {user.role}")
    print(f"  Apps: {apps}")
    print(f"  Permissions: {len(perms)} permissions")

# Save to JSON file
output_file = "production_users_export.json"
with open(output_file, "w") as f:
    json.dump(
        {"exported_at": datetime.now().isoformat(), "users": users_data}, f, indent=2
    )

print(f"\n{'='*80}")
print(f"✓ Exported {len(users_data)} users to {output_file}")
print(f"\nNext steps:")
print(f"  1. Download this file from Render")
print(f"  2. Place it in your local project directory")
print(f"  3. Run: python import_production_users.py")
