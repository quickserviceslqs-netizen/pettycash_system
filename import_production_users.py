"""
Import production users into local database
Run this locally after downloading production_users_export.json from Render
"""

import json
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pettycash_system.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from accounts.models import App

User = get_user_model()

# Check if export file exists
import_file = "production_users_export.json"

if not os.path.exists(import_file):
    print(f"❌ Error: {import_file} not found!")
    print(f"\nPlease:")
    print(f"  1. Run export_production_users.py on Render")
    print(f"  2. Download the generated production_users_export.json file")
    print(f"  3. Place it in this directory: {os.getcwd()}")
    exit(1)

print("Importing production users to local database...")
print("=" * 80)

with open(import_file, "r") as f:
    data = json.load(f)

print(f"\nExported from production at: {data['exported_at']}")
print(f"Total users to import: {len(data['users'])}")

# Ask for confirmation
response = input(
    f"\nThis will UPDATE existing users and CREATE new ones. Continue? (yes/no): "
)
if response.lower() != "yes":
    print("Import cancelled")
    exit(0)

# Default password for imported users (they should reset it)
DEFAULT_PASSWORD = "ChangeMe@123"

imported = 0
updated = 0
errors = []

for user_data in data["users"]:
    try:
        username = user_data["username"]

        # Check if user exists
        try:
            user = User.objects.get(username=username)
            print(f"\n✓ Updating existing user: {username}")
            action = "updated"
        except User.DoesNotExist:
            # Create new user
            user = User.objects.create_user(
                username=username, email=user_data["email"], password=DEFAULT_PASSWORD
            )
            print(f"\n✓ Created new user: {username}")
            print(f"  Password set to: {DEFAULT_PASSWORD}")
            action = "created"

        # Update user fields
        user.email = user_data["email"]
        user.first_name = user_data["first_name"]
        user.last_name = user_data["last_name"]
        user.is_superuser = user_data["is_superuser"]
        user.is_staff = user_data["is_staff"]
        user.is_active = user_data["is_active"]
        user.role = user_data["role"]
        user.save()

        print(f"  Email: {user.email}")
        print(f"  Superuser: {user.is_superuser}")
        print(f"  Role: {user.role}")

        # Assign apps
        user.assigned_apps.clear()
        for app_name in user_data["assigned_apps"]:
            try:
                app = App.objects.get(name=app_name)
                user.assigned_apps.add(app)
                print(f"  ✓ Assigned app: {app_name}")
            except App.DoesNotExist:
                print(f"  ⚠️  App '{app_name}' not found - skipping")

        # Assign permissions
        user.user_permissions.clear()
        for perm_data in user_data["permissions"]:
            try:
                ct = ContentType.objects.get(
                    app_label=perm_data["app_label"], model__isnull=False
                )
                # Find the permission - try multiple models
                perm = None
                for content_type in ContentType.objects.filter(
                    app_label=perm_data["app_label"]
                ):
                    try:
                        perm = Permission.objects.get(
                            codename=perm_data["codename"], content_type=content_type
                        )
                        break
                    except Permission.DoesNotExist:
                        continue

                if perm:
                    user.user_permissions.add(perm)
                else:
                    print(
                        f"  ⚠️  Permission {perm_data['app_label']}.{perm_data['codename']} not found"
                    )
            except Exception as e:
                print(f"  ⚠️  Error adding permission: {e}")

        print(f"  ✓ Assigned {user.user_permissions.count()} permissions")

        # Assign groups
        for group_name in user_data["groups"]:
            try:
                group, created = Group.objects.get_or_create(name=group_name)
                user.groups.add(group)
                print(f"  ✓ Added to group: {group_name}")
            except Exception as e:
                print(f"  ⚠️  Error adding to group: {e}")

        if action == "created":
            imported += 1
        else:
            updated += 1

    except Exception as e:
        error_msg = f"Error importing {user_data['username']}: {str(e)}"
        errors.append(error_msg)
        print(f"\n❌ {error_msg}")

print(f"\n{'='*80}")
print(f"IMPORT SUMMARY")
print(f"{'='*80}")
print(f"  Created: {imported} users")
print(f"  Updated: {updated} users")
print(f"  Errors: {len(errors)}")

if errors:
    print(f"\nErrors encountered:")
    for error in errors:
        print(f"  - {error}")

print(f"\n✓ Import complete!")

if imported > 0:
    print(f"\nNew users created with default password: {DEFAULT_PASSWORD}")
    print(f"Users should change their password on first login.")

print(f"\nCurrent users in database:")
for user in User.objects.all().order_by("username"):
    apps = list(user.assigned_apps.values_list("name", flat=True))
    print(f"\n  {user.username}")
    print(f"    Superuser: {user.is_superuser}")
    print(f"    Apps: {apps}")
    print(f"    Permissions: {user.user_permissions.count()}")
