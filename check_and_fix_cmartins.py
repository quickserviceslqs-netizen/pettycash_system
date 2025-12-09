"""
Check and optionally fix Cmartins user permissions
Run this on Render shell or locally after creating the user
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pettycash_system.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from accounts.models import App
from treasury.models import Payment, TreasuryFund

User = get_user_model()

print("=" * 80)
print("CHECKING CMARTINS USER")
print("=" * 80)

try:
    cmartins = User.objects.get(username__iexact="Cmartins")
    print(f"\n✓ Found user: {cmartins.username}")
    print(f"\nCurrent Status:")
    print(f"  Is Superuser: {cmartins.is_superuser}")
    print(f"  Is Staff: {cmartins.is_staff}")
    print(f"  Role: {cmartins.role}")
    print(f"  Apps: {list(cmartins.assigned_apps.values_list('name', flat=True))}")

    if cmartins.is_superuser:
        print(f"\n{'='*80}")
        print(f"⚠️  WARNING: Cmartins is a SUPERUSER")
        print(f"{'='*80}")
        print(f"\nSuperusers bypass ALL permission checks including:")
        print(f"  - App assignment checks")
        print(f"  - Django permission checks")
        print(f"  - Custom permission logic")
        print(f"\nThis is why Cmartins can access everything.")

        response = input(
            f"\nDo you want to REMOVE superuser status from Cmartins? (yes/no): "
        )
        if response.lower() == "yes":
            cmartins.is_superuser = False
            cmartins.save()
            print(f"\n✓ Removed superuser status from Cmartins")
            print(f"  Cmartins will now follow normal permission checks")
        else:
            print(
                f"\n✓ Keeping superuser status - Cmartins will continue to have full access"
            )
            exit(0)

    # Check if has apps assigned
    apps = list(cmartins.assigned_apps.values_list("name", flat=True))
    if not apps:
        print(f"\n⚠️  Cmartins has NO apps assigned")
        print(f"\nAvailable apps:")
        for app in App.objects.filter(is_active=True):
            print(f"  - {app.name}")

        response = input(f"\nDo you want to assign apps to Cmartins? (yes/no): ")
        if response.lower() == "yes":
            print(f"\nWhich apps? (comma-separated, e.g., treasury,transactions):")
            apps_input = input("> ")
            app_names = [a.strip() for a in apps_input.split(",")]

            for app_name in app_names:
                try:
                    app = App.objects.get(name=app_name)
                    cmartins.assigned_apps.add(app)
                    print(f"  ✓ Assigned {app_name} app")
                except App.DoesNotExist:
                    print(f"  ❌ App '{app_name}' not found")
    else:
        print(f"\n✓ Cmartins has apps assigned: {apps}")

    # Check permissions
    perms = cmartins.user_permissions.all()
    if not perms.exists():
        print(f"\n⚠️  Cmartins has NO Django permissions assigned")

        response = input(f"\nDo you want to add treasury permissions? (yes/no): ")
        if response.lower() == "yes":
            # Add view permissions
            ct_fund = ContentType.objects.get_for_model(TreasuryFund)
            ct_payment = ContentType.objects.get_for_model(Payment)

            view_fund = Permission.objects.get(
                codename="view_treasuryfund", content_type=ct_fund
            )
            view_payment = Permission.objects.get(
                codename="view_payment", content_type=ct_payment
            )

            cmartins.user_permissions.add(view_fund, view_payment)
            print(f"  ✓ Added view_treasuryfund permission")
            print(f"  ✓ Added view_payment permission")

            response = input(
                f"\nAdd change_payment permission (for executing payments)? (yes/no): "
            )
            if response.lower() == "yes":
                change_payment = Permission.objects.get(
                    codename="change_payment", content_type=ct_payment
                )
                cmartins.user_permissions.add(change_payment)
                print(f"  ✓ Added change_payment permission")
    else:
        print(f"\n✓ Cmartins has {perms.count()} Django permissions")

    print(f"\n{'='*80}")
    print(f"FINAL STATUS FOR CMARTINS")
    print(f"{'='*80}")
    print(f"  Is Superuser: {cmartins.is_superuser}")
    print(f"  Apps: {list(cmartins.assigned_apps.values_list('name', flat=True))}")
    print(f"  Permissions: {cmartins.user_permissions.count()} permissions")

    if cmartins.is_superuser:
        print(f"\n  🔓 FULL ACCESS (Superuser)")
    else:
        print(f"\n  ✓ Following normal permission checks")

except User.DoesNotExist:
    print(f"\n❌ User 'Cmartins' not found")
    print(f"\nDo you want to CREATE Cmartins user? (yes/no): ")
    response = input("> ")

    if response.lower() == "yes":
        print(f"\nEnter email for Cmartins:")
        email = input("> ")
        print(f"\nEnter password:")
        password = input("> ")

        cmartins = User.objects.create_user(
            username="Cmartins", email=email, password=password, role="staff"
        )
        print(f"\n✓ Created user Cmartins")
        print(f"  Username: Cmartins")
        print(f"  Password: {password}")
        print(f"\nRun this script again to assign apps and permissions")
