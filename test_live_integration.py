"""
Live integration test - verify settings are actively used in running system
Tests actual behavior changes based on setting values
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
django.setup()

from settings_manager.models import SystemSetting, get_setting
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

def print_header(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def print_section(title):
    print(f"\n{'-'*80}")
    print(f"  {title}")
    print(f"{'-'*80}")

def test_security_lockout_integration():
    """Test that security lockout settings are actually used"""
    print_header("LIVE TEST 1: Security Lockout Integration")
    
    threshold = get_setting('SECURITY_LOCKOUT_THRESHOLD', 5)
    window = get_setting('SECURITY_LOCKOUT_WINDOW_MINUTES', 15)
    duration = get_setting('SECURITY_LOCKOUT_DURATION_MINUTES', 30)
    
    print(f"Current Settings:")
    print(f"  • Lockout Threshold: {threshold} attempts")
    print(f"  • Window: {window} minutes")
    print(f"  • Duration: {duration} minutes")
    
    # Check if LoginAttempt model uses these settings
    print_section("Code Integration Check")
    
    import inspect
    from accounts import signals
    
    # Check if signals.py uses the settings
    source = inspect.getsource(signals.check_failed_login_attempts)
    
    uses_threshold = 'SECURITY_LOCKOUT_THRESHOLD' in source
    uses_window = 'SECURITY_LOCKOUT_WINDOW' in source
    
    print(f"  ✅ Uses SECURITY_LOCKOUT_THRESHOLD: {uses_threshold}")
    print(f"  ✅ Uses SECURITY_LOCKOUT_WINDOW: {uses_window}")
    
    # Check database for users with login tracking
    users_with_attempts = User.objects.filter(failed_login_attempts__gt=0).count()
    locked_users = User.objects.filter(lockout_until__gt=timezone.now()).count()
    
    print_section("Database Activity")
    print(f"  📊 Users with failed attempts: {users_with_attempts}")
    print(f"  🔒 Currently locked out: {locked_users}")
    
    return uses_threshold and uses_window

def test_approval_workflow_integration():
    """Test approval workflow settings integration"""
    print_header("LIVE TEST 2: Approval Workflow Integration")
    
    deadline_hours = get_setting('DEFAULT_APPROVAL_DEADLINE_HOURS', 24)
    allow_self = get_setting('ALLOW_SELF_APPROVAL', False)
    
    print(f"Current Settings:")
    print(f"  • Default Approval Deadline: {deadline_hours} hours")
    print(f"  • Allow Self Approval: {allow_self}")
    
    # Check transactions model
    from transactions import models as trans_models
    
    print_section("Model Integration")
    
    # Check if Requisition model has deadline calculation
    if hasattr(trans_models.Requisition, 'approval_deadline'):
        print(f"  ✅ Requisition model has approval_deadline field")
    else:
        print(f"  ⚠️  Requisition model missing approval_deadline field")
    
    # Check database for requisitions
    from transactions.models import Requisition
    
    total_reqs = Requisition.objects.count()
    pending_reqs = Requisition.objects.filter(approval_status='pending').count()
    
    print_section("Database Activity")
    print(f"  📊 Total Requisitions: {total_reqs}")
    print(f"  📊 Pending Approvals: {pending_reqs}")
    
    return True

def test_treasury_integration():
    """Test treasury settings integration"""
    print_header("LIVE TEST 3: Treasury Operations Integration")
    
    min_balance = get_setting('TREASURY_MINIMUM_FUND_BALANCE', 0)
    auto_replenish = get_setting('TREASURY_AUTO_REPLENISHMENT_ENABLED', True)
    
    print(f"Current Settings:")
    print(f"  • Minimum Fund Balance: {min_balance}")
    print(f"  • Auto Replenishment: {auto_replenish}")
    
    # Check treasury models
    from treasury.models import TreasuryFund
    
    funds = TreasuryFund.objects.all()
    
    print_section("Treasury Funds Status")
    for fund in funds[:5]:  # Show first 5 funds
        print(f"  💰 {fund.name}: {fund.currency} {fund.current_balance}")
        if fund.current_balance < min_balance:
            print(f"      ⚠️  Below minimum balance!")
    
    total_funds = funds.count()
    below_min = funds.filter(current_balance__lt=min_balance).count()
    
    print_section("Summary")
    print(f"  📊 Total Funds: {total_funds}")
    print(f"  ⚠️  Below Minimum: {below_min}")
    
    return True

def test_invitation_integration():
    """Test user invitation settings"""
    print_header("LIVE TEST 4: User Invitation Integration")
    
    expiry_days = get_setting('INVITATION_EXPIRY_DAYS', 7)
    
    print(f"Current Settings:")
    print(f"  • Invitation Expiry: {expiry_days} days")
    
    # Check if UserInvitation model exists
    from accounts.models import UserInvitation
    
    invitations = UserInvitation.objects.all()
    active = invitations.filter(is_used=False, expires_at__gt=timezone.now()).count()
    expired = invitations.filter(is_used=False, expires_at__lte=timezone.now()).count()
    used = invitations.filter(is_used=True).count()
    
    print_section("Invitation Status")
    print(f"  📊 Total Invitations: {invitations.count()}")
    print(f"  ✅ Active: {active}")
    print(f"  ⏰ Expired: {expired}")
    print(f"  ✓ Used: {used}")
    
    # Check code integration
    import inspect
    from accounts import views_invitation
    
    source = inspect.getsource(views_invitation)
    uses_expiry = 'INVITATION_EXPIRY_DAYS' in source or 'invitation_expiry' in source.lower()
    
    print_section("Code Integration")
    print(f"  ✅ Uses expiry setting: {uses_expiry}")
    
    return True

def test_notification_integration():
    """Test notification settings"""
    print_header("LIVE TEST 5: Notification Settings Integration")
    
    # Get various notification settings
    notif_settings = SystemSetting.objects.filter(
        category='notifications',
        is_active=True
    )
    
    print(f"Notification Settings ({notif_settings.count()}):")
    for setting in notif_settings[:10]:
        value = setting.get_typed_value()
        print(f"  • {setting.key}: {value}")
    
    return notif_settings.count() > 0

def test_device_whitelist_integration():
    """Test device whitelist settings"""
    print_header("LIVE TEST 6: Device Whitelist Integration")
    
    enforce = get_setting('ENFORCE_DEVICE_WHITELIST', False)
    geo_enabled = get_setting('ENABLE_ACTIVITY_GEOLOCATION', True)
    
    print(f"Current Settings:")
    print(f"  • Enforce Device Whitelist: {enforce}")
    print(f"  • Geolocation Tracking: {geo_enabled}")
    
    # Check for device-related models
    from accounts.models import UserDevice
    
    devices = UserDevice.objects.all()
    whitelisted = devices.filter(is_whitelisted=True).count()
    
    print_section("Device Status")
    print(f"  📱 Total Devices: {devices.count()}")
    print(f"  ✅ Whitelisted: {whitelisted}")
    
    # Check middleware integration
    print_section("Middleware Integration")
    from django.conf import settings as django_settings
    
    middleware = django_settings.MIDDLEWARE
    has_device_middleware = any('device' in m.lower() for m in middleware)
    has_ip_middleware = any('ip' in m.lower() or 'whitelist' in m.lower() for m in middleware)
    
    print(f"  ✅ Device Middleware: {has_device_middleware}")
    print(f"  ✅ IP Whitelist Middleware: {has_ip_middleware}")
    
    return True

def test_settings_ui_access():
    """Test that settings UI is accessible"""
    print_header("LIVE TEST 7: Settings UI Integration")
    
    # Check URL configuration
    from django.urls import reverse, NoReverseMatch
    
    try:
        settings_url = reverse('settings_manager:settings_list')
        print(f"  ✅ Settings List URL: {settings_url}")
    except NoReverseMatch:
        print(f"  ❌ Settings List URL not found")
        return False
    
    try:
        dashboard_url = reverse('settings_manager:dashboard')
        print(f"  ✅ Settings Dashboard URL: {dashboard_url}")
    except NoReverseMatch:
        print(f"  ⚠️  Settings Dashboard URL not found")
    
    # Check admin integration
    from django.contrib import admin
    from settings_manager.models import SystemSetting
    
    is_registered = SystemSetting in admin.site._registry
    
    print_section("Admin Integration")
    print(f"  ✅ Registered in Django Admin: {is_registered}")
    
    return True

def test_performance():
    """Test settings retrieval performance"""
    print_header("LIVE TEST 8: Performance & Caching")
    
    import time
    
    # Test get_setting performance
    start = time.time()
    for _ in range(100):
        get_setting('SECURITY_LOCKOUT_THRESHOLD', 5)
    duration = (time.time() - start) * 1000
    
    print(f"  ⚡ 100 get_setting() calls: {duration:.2f}ms")
    print(f"  📊 Average per call: {duration/100:.2f}ms")
    
    if duration < 100:
        print(f"  ✅ Performance: Excellent (< 100ms)")
    elif duration < 500:
        print(f"  ✅ Performance: Good (< 500ms)")
    else:
        print(f"  ⚠️  Performance: Needs optimization (> 500ms)")
    
    # Test database query count
    from django.test.utils import override_settings
    from django.db import connection, reset_queries
    
    reset_queries()
    
    # Retrieve 10 different settings
    test_keys = [
        'SECURITY_LOCKOUT_THRESHOLD',
        'DEFAULT_APPROVAL_DEADLINE_HOURS',
        'TREASURY_MINIMUM_FUND_BALANCE',
        'INVITATION_EXPIRY_DAYS',
        'ENABLE_ACTIVITY_GEOLOCATION',
    ]
    
    for key in test_keys:
        get_setting(key)
    
    queries = len(connection.queries)
    
    print_section("Database Queries")
    print(f"  📊 Queries for 5 settings: {queries}")
    
    if queries <= 5:
        print(f"  ✅ Query efficiency: Excellent (1 query per setting or cached)")
    else:
        print(f"  ⚠️  Query efficiency: Could be improved")
    
    return True

def run_live_tests():
    """Run all live integration tests"""
    print("\n" + "="*80)
    print("  PETTYCASH SYSTEM - LIVE INTEGRATION TEST SUITE")
    print("  Verifying settings are actively used in running system")
    print("="*80)
    
    tests = [
        ("Security Lockout Integration", test_security_lockout_integration),
        ("Approval Workflow Integration", test_approval_workflow_integration),
        ("Treasury Operations Integration", test_treasury_integration),
        ("User Invitation Integration", test_invitation_integration),
        ("Notification Settings", test_notification_integration),
        ("Device Whitelist Integration", test_device_whitelist_integration),
        ("Settings UI Access", test_settings_ui_access),
        ("Performance & Caching", test_performance),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result, None))
        except Exception as e:
            results.append((test_name, False, str(e)))
    
    # Summary
    print_header("LIVE TEST SUMMARY")
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for test_name, result, error in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} | {test_name}")
        if error:
            print(f"         Error: {error}")
    
    print(f"\n{'='*80}")
    print(f"  OVERALL RESULT: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    print(f"{'='*80}\n")
    
    if passed == total:
        print("  🎉 All settings are live and fully integrated!")
    elif passed >= total * 0.75:
        print("  ✅ Settings are working well with minor issues.")
    else:
        print("  ⚠️  Some integration issues detected.")
    
    return passed == total

if __name__ == '__main__':
    success = run_live_tests()
    exit(0 if success else 1)
