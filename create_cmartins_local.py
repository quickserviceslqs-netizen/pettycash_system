"""
Quick script to create Cmartins user locally for testing
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from accounts.models import App
from treasury.models import TreasuryFund, Payment

User = get_user_model()

# Create or update Cmartins
try:
    cmartins = User.objects.get(username='Cmartins')
    print("Updating existing Cmartins user...")
except User.DoesNotExist:
    cmartins = User.objects.create_user(
        username='Cmartins',
        email='cmartins@example.com',
        password='Cmartins@123',
        role='staff'
    )
    print("Created new Cmartins user")

# Make regular user (NOT superuser) to test permissions
cmartins.is_superuser = False
cmartins.is_staff = True
cmartins.save()

# Assign treasury app
treasury_app = App.objects.get(name='treasury')
cmartins.assigned_apps.add(treasury_app)

# Assign permissions
ct_fund = ContentType.objects.get_for_model(TreasuryFund)
ct_payment = ContentType.objects.get_for_model(Payment)

view_fund = Permission.objects.get(codename='view_treasuryfund', content_type=ct_fund)
view_payment = Permission.objects.get(codename='view_payment', content_type=ct_payment)
change_payment = Permission.objects.get(codename='change_payment', content_type=ct_payment)

cmartins.user_permissions.add(view_fund, view_payment, change_payment)

print(f"\n✓ Cmartins user configured:")
print(f"  Username: Cmartins")
print(f"  Password: Cmartins@123")
print(f"  Is Superuser: {cmartins.is_superuser}")
print(f"  Apps: {list(cmartins.assigned_apps.values_list('name', flat=True))}")
print(f"  Permissions: view_treasuryfund, view_payment, change_payment")
print(f"\nYou can now login as Cmartins to test permissions")
