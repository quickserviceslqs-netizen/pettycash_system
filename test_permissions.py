"""
Comprehensive Permission Testing Script
Tests all permission checks across transactions, treasury, workflow, and reports apps
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from accounts.models import App
from treasury.models import TreasuryFund, Payment
from transactions.models import Requisition
from workflow.models import ApprovalThreshold
from decimal import Decimal

User = get_user_model()

class PermissionTester:
    def __init__(self):
        self.test_results = []
        self.users_created = []
        
    def print_header(self, title):
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)
        
    def print_test(self, name, passed, details=""):
        status = "✓ PASS" if passed else "✗ FAIL"
        self.test_results.append((name, passed))
        print(f"{status}: {name}")
        if details:
            print(f"       {details}")
    
    def create_test_users(self):
        """Create test users with various permission levels"""
        self.print_header("Creating Test Users")
        
        # Clean up existing test users
        User.objects.filter(username__startswith='test_').delete()
        
        # 1. Basic user - no apps, no permissions
        basic_user = User.objects.create_user(
            username='test_basic',
            email='basic@test.com',
            password='Test@123',
            role='staff'
        )
        self.users_created.append(('Basic User (No Apps/Permissions)', basic_user))
        print(f"✓ Created: test_basic (no apps, no permissions)")
        
        # 2. Treasury user - treasury app assigned, limited permissions
        treasury_user = User.objects.create_user(
            username='test_treasury',
            email='treasury@test.com',
            password='Test@123',
            role='treasury_officer'
        )
        treasury_app = App.objects.get(name='treasury')
        treasury_user.assigned_apps.add(treasury_app)
        
        # Add only view permission, not change
        ct = ContentType.objects.get_for_model(Payment)
        view_perm = Permission.objects.get(codename='view_payment', content_type=ct)
        treasury_user.user_permissions.add(view_perm)
        
        self.users_created.append(('Treasury User (View Only)', treasury_user))
        print(f"✓ Created: test_treasury (treasury app + view_payment only)")
        
        # 3. Full treasury user - all treasury permissions
        full_treasury_user = User.objects.create_user(
            username='test_treasury_full',
            email='treasuryfull@test.com',
            password='Test@123',
            role='treasury_officer'
        )
        full_treasury_user.assigned_apps.add(treasury_app)
        
        # Add all treasury permissions
        for perm in Permission.objects.filter(content_type__app_label='treasury'):
            full_treasury_user.user_permissions.add(perm)
        
        self.users_created.append(('Full Treasury User', full_treasury_user))
        print(f"✓ Created: test_treasury_full (treasury app + all permissions)")
        
        # 4. Transactions user - transactions app, no workflow app
        transactions_user = User.objects.create_user(
            username='test_transactions',
            email='transactions@test.com',
            password='Test@123',
            role='requisitioner'
        )
        transactions_app = App.objects.get(name='transactions')
        transactions_user.assigned_apps.add(transactions_app)
        
        # Add requisition permissions
        ct = ContentType.objects.get_for_model(Requisition)
        for codename in ['view_requisition', 'add_requisition']:
            perm = Permission.objects.get(codename=codename, content_type=ct)
            transactions_user.user_permissions.add(perm)
        
        self.users_created.append(('Transactions User', transactions_user))
        print(f"✓ Created: test_transactions (transactions app + view/add requisition)")
        
        # 5. Workflow user - workflow app assigned
        workflow_user = User.objects.create_user(
            username='test_workflow',
            email='workflow@test.com',
            password='Test@123',
            role='approver'
        )
        workflow_app = App.objects.get(name='workflow')
        workflow_user.assigned_apps.add(workflow_app)
        
        # Add workflow view permission
        ct = ContentType.objects.get_for_model(ApprovalThreshold)
        view_perm = Permission.objects.get(codename='view_approvalthreshold', content_type=ct)
        workflow_user.user_permissions.add(view_perm)
        
        self.users_created.append(('Workflow User', workflow_user))
        print(f"✓ Created: test_workflow (workflow app + view_approvalthreshold)")
        
        print(f"\n✓ Created {len(self.users_created)} test users")
        
    def test_app_assignment(self):
        """Test that users can only see apps they're assigned to"""
        self.print_header("Testing App Assignment System")
        
        from accounts.permissions import get_user_apps
        
        # Test basic user - should have no apps
        basic_user = User.objects.get(username='test_basic')
        apps = get_user_apps(basic_user)
        self.print_test(
            "Basic user has no apps",
            len(apps) == 0,
            f"Expected 0 apps, got {len(apps)}"
        )
        
        # Test treasury user - should have treasury app
        treasury_user = User.objects.get(username='test_treasury')
        apps = get_user_apps(treasury_user)
        self.print_test(
            "Treasury user has treasury app",
            len(apps) == 1 and 'treasury' in apps,
            f"Expected 1 app (treasury), got {apps}"
        )
        
        # Test workflow user - should have workflow app
        workflow_user = User.objects.get(username='test_workflow')
        apps = get_user_apps(workflow_user)
        self.print_test(
            "Workflow user has workflow app",
            len(apps) == 1 and 'workflow' in apps,
            f"Expected 1 app (workflow), got {apps}"
        )
        
        # Test superuser - should have all apps
        superuser = User.objects.filter(is_superuser=True).first()
        if superuser:
            apps = get_user_apps(superuser)
            self.print_test(
                "Superuser has all apps",
                len(apps) == 4,
                f"Expected 4 apps, got {len(apps)}: {apps}"
            )
    
    def test_treasury_permissions(self):
        """Test treasury critical action permissions"""
        self.print_header("Testing Treasury Permission Enforcement")
        
        # Get test users
        view_only = User.objects.get(username='test_treasury')
        full_access = User.objects.get(username='test_treasury_full')
        no_app = User.objects.get(username='test_basic')
        
        # Test view_payment permission
        self.print_test(
            "View-only user has view_payment permission",
            view_only.has_perm('treasury.view_payment'),
            "Should be able to view payments"
        )
        
        self.print_test(
            "View-only user lacks change_payment permission",
            not view_only.has_perm('treasury.change_payment'),
            "Should NOT be able to execute/send OTP"
        )
        
        # Test full access user
        self.print_test(
            "Full access user has change_payment permission",
            full_access.has_perm('treasury.change_payment'),
            "Should be able to execute payments and send OTP"
        )
        
        self.print_test(
            "Full access user has add_treasuryfund permission",
            full_access.has_perm('treasury.add_treasuryfund'),
            "Should be able to create treasury funds"
        )
        
        # Test user without app
        self.print_test(
            "User without treasury app has no permissions",
            not no_app.has_perm('treasury.view_payment'),
            "Basic user should have no treasury access"
        )
        
    def test_transactions_permissions(self):
        """Test transactions permission enforcement"""
        self.print_header("Testing Transactions Permission Enforcement")
        
        transactions_user = User.objects.get(username='test_transactions')
        no_app = User.objects.get(username='test_basic')
        
        # Test requisition permissions
        self.print_test(
            "Transactions user has view_requisition permission",
            transactions_user.has_perm('transactions.view_requisition'),
            "Should be able to view requisitions"
        )
        
        self.print_test(
            "Transactions user has add_requisition permission",
            transactions_user.has_perm('transactions.add_requisition'),
            "Should be able to create requisitions"
        )
        
        self.print_test(
            "Transactions user lacks change_requisition permission",
            not transactions_user.has_perm('transactions.change_requisition'),
            "Should NOT be able to approve/override requisitions"
        )
        
        # Test user without app
        self.print_test(
            "User without transactions app has no permissions",
            not no_app.has_perm('transactions.view_requisition'),
            "Basic user should have no transactions access"
        )
    
    def test_workflow_access(self):
        """Test workflow app access"""
        self.print_header("Testing Workflow App Access")
        
        workflow_user = User.objects.get(username='test_workflow')
        no_app = User.objects.get(username='test_basic')
        
        # Test workflow permissions
        self.print_test(
            "Workflow user has view_approvalthreshold permission",
            workflow_user.has_perm('workflow.view_approvalthreshold'),
            "Should be able to view approval thresholds"
        )
        
        # Test user without app
        self.print_test(
            "User without workflow app has no permissions",
            not no_app.has_perm('workflow.view_approvalthreshold'),
            "Basic user should have no workflow access"
        )
        
        # Test app assignment
        from accounts.permissions import get_user_apps
        apps = get_user_apps(workflow_user)
        has_workflow = 'workflow' in apps
        
        self.print_test(
            "Workflow user has workflow app assigned",
            has_workflow,
            "Should have workflow in assigned apps"
        )
    
    def test_superuser_bypass(self):
        """Test that superuser bypasses all permission checks"""
        self.print_header("Testing Superuser Bypass")
        
        superuser = User.objects.filter(is_superuser=True).first()
        if not superuser:
            print("⚠ No superuser found - skipping superuser tests")
            return
        
        # Test all permission checks
        self.print_test(
            "Superuser has treasury.change_payment permission",
            superuser.has_perm('treasury.change_payment'),
            "Superuser should have all permissions"
        )
        
        self.print_test(
            "Superuser has transactions.change_requisition permission",
            superuser.has_perm('transactions.change_requisition'),
            "Superuser should have all permissions"
        )
        
        self.print_test(
            "Superuser has workflow.view_approvalthreshold permission",
            superuser.has_perm('workflow.view_approvalthreshold'),
            "Superuser should have all permissions"
        )
        
        # Test app access
        from accounts.permissions import get_user_apps
        apps = get_user_apps(superuser)
        
        self.print_test(
            "Superuser has access to all apps",
            len(apps) == 4,
            f"Expected 4 apps, got {len(apps)}: {apps}"
        )
    
    def print_summary(self):
        """Print test summary"""
        self.print_header("Test Summary")
        
        passed = sum(1 for _, result in self.test_results if result)
        total = len(self.test_results)
        failed = total - passed
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        if failed > 0:
            print("\n❌ Failed Tests:")
            for name, result in self.test_results:
                if not result:
                    print(f"  - {name}")
        else:
            print("\n✅ All tests passed!")
        
        print("\n" + "=" * 80)
        print("Test Users Created (use these credentials to test in UI):")
        print("=" * 80)
        for desc, user in self.users_created:
            print(f"\n{desc}:")
            print(f"  Username: {user.username}")
            print(f"  Password: Test@123")
            print(f"  Role: {user.role}")
            print(f"  Apps: {', '.join([app.name for app in user.assigned_apps.all()])}")
        
        print("\nSuperuser Account:")
        superuser = User.objects.filter(is_superuser=True).first()
        if superuser:
            print(f"  Username: {superuser.username}")
            print(f"  Password: Super@123456")
            print(f"  Apps: All (automatic)")
    
    def cleanup(self):
        """Optional cleanup - remove test users"""
        print("\n" + "=" * 80)
        response = input("Remove test users? (y/n): ")
        if response.lower() == 'y':
            count = User.objects.filter(username__startswith='test_').delete()[0]
            print(f"✓ Removed {count} test users")
        else:
            print("✓ Test users preserved for manual testing")

def main():
    tester = PermissionTester()
    
    try:
        # Run all tests
        tester.create_test_users()
        tester.test_app_assignment()
        tester.test_treasury_permissions()
        tester.test_transactions_permissions()
        tester.test_workflow_access()
        tester.test_superuser_bypass()
        
        # Print summary
        tester.print_summary()
        
        # Optional cleanup
        tester.cleanup()
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
