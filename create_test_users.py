"""
Create test users for manual UI testing
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from accounts.models import App
from treasury.models import Payment
from transactions.models import Requisition
from workflow.models import ApprovalThreshold

User = get_user_model()

# Clean up existing test users
User.objects.filter(username__startswith='test_').delete()

print("Creating test users for UI testing...")
print("=" * 80)

# 1. Basic user - no apps, no permissions
basic_user = User.objects.create_user(
    username='test_basic',
    email='basic@test.com',
    password='Test@123',
    role='staff'
)
print("\n1. Basic User (No Access)")
print(f"   Username: test_basic")
print(f"   Password: Test@123")
print(f"   Apps: None")
print(f"   Permissions: None")
print(f"   Expected: Should NOT access any app features")

# 2. Treasury user - treasury app assigned, view only
treasury_user = User.objects.create_user(
    username='test_treasury',
    email='treasury@test.com',
    password='Test@123',
    role='treasury_officer'
)
treasury_app = App.objects.get(name='treasury')
treasury_user.assigned_apps.add(treasury_app)

ct = ContentType.objects.get_for_model(Payment)
view_perm = Permission.objects.get(codename='view_payment', content_type=ct)
treasury_user.user_permissions.add(view_perm)

print("\n2. Treasury User (View Only)")
print(f"   Username: test_treasury")
print(f"   Password: Test@123")
print(f"   Apps: treasury")
print(f"   Permissions: view_payment")
print(f"   Expected: Can view treasury, CANNOT execute/send OTP")

# 3. Full treasury user - all treasury permissions
full_treasury_user = User.objects.create_user(
    username='test_treasury_full',
    email='treasuryfull@test.com',
    password='Test@123',
    role='treasury_officer'
)
full_treasury_user.assigned_apps.add(treasury_app)

for perm in Permission.objects.filter(content_type__app_label='treasury'):
    full_treasury_user.user_permissions.add(perm)

print("\n3. Full Treasury User (All Permissions)")
print(f"   Username: test_treasury_full")
print(f"   Password: Test@123")
print(f"   Apps: treasury")
print(f"   Permissions: All treasury permissions")
print(f"   Expected: Can execute payments, send OTP, reconcile funds")

# 4. Transactions user - view and add requisitions only
transactions_user = User.objects.create_user(
    username='test_transactions',
    email='transactions@test.com',
    password='Test@123',
    role='requisitioner'
)
transactions_app = App.objects.get(name='transactions')
transactions_user.assigned_apps.add(transactions_app)

ct = ContentType.objects.get_for_model(Requisition)
for codename in ['view_requisition', 'add_requisition']:
    perm = Permission.objects.get(codename=codename, content_type=ct)
    transactions_user.user_permissions.add(perm)

print("\n4. Transactions User (Create/View Only)")
print(f"   Username: test_transactions")
print(f"   Password: Test@123")
print(f"   Apps: transactions")
print(f"   Permissions: view_requisition, add_requisition")
print(f"   Expected: Can create requisitions, CANNOT approve/override")

# 5. Workflow user
workflow_user = User.objects.create_user(
    username='test_workflow',
    email='workflow@test.com',
    password='Test@123',
    role='approver'
)
workflow_app = App.objects.get(name='workflow')
workflow_user.assigned_apps.add(workflow_app)

ct = ContentType.objects.get_for_model(ApprovalThreshold)
view_perm = Permission.objects.get(codename='view_approvalthreshold', content_type=ct)
workflow_user.user_permissions.add(view_perm)

print("\n5. Workflow User (View Only)")
print(f"   Username: test_workflow")
print(f"   Password: Test@123")
print(f"   Apps: workflow")
print(f"   Permissions: view_approvalthreshold")
print(f"   Expected: Can access workflow app")

print("\n" + "=" * 80)
print("\nSuperuser Account (Full Access):")
superuser = User.objects.filter(is_superuser=True).first()
if superuser:
    print(f"   Username: {superuser.username}")
    print(f"   Password: Super@123456")
    print(f"   Apps: All (automatic)")
    print(f"   Expected: Can access everything")

print("\n" + "=" * 80)
print("\n✅ Test users created successfully!")
print("\nUse these credentials to test permission enforcement in the UI.")
print("Verify that each user can only access features matching their permissions.")
