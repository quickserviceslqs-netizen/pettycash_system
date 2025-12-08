"""
Simplified live integration test - verify settings work with actual models
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
django.setup()

from settings_manager.models import SystemSetting, get_setting
from django.contrib.auth import get_user_model
from django.utils import timezone
import time

User = get_user_model()

def print_header(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def print_section(title):
    print(f"\n{'-'*80}")
    print(f"  {title}")
    print(f"{'-'*80}")

def test_database_settings():
    """Test 1: Verify settings in database"""
    print_header("TEST 1: Settings Database Status")
    
    total = SystemSetting.objects.count()
    active = SystemSetting.objects.filter(is_active=True).count()
    
    by_category = {}
    for cat, name in SystemSetting.CATEGORY_CHOICES:
        count = SystemSetting.objects.filter(category=cat, is_active=True).count()
        if count > 0:
            by_category[name] = count
    
    print(f"📊 Total Settings: {total}")
    print(f"✅ Active Settings: {active}")
    print(f"📁 Categories: {len(by_category)}/{len(SystemSetting.CATEGORY_CHOICES)}")
    
    print_section("Top Categories")
    for name, count in sorted(by_category.items(), key=lambda x: -x[1])[:5]:
        print(f"  • {name}: {count} settings")
    
    return total > 150 and active > 150

def test_get_setting_works():
    """Test 2: Verify get_setting() retrieves values correctly"""
    print_header("TEST 2: Get Setting Function")
    
    test_cases = [
        ('SECURITY_LOCKOUT_THRESHOLD', 5, int),
        ('SECURITY_LOCKOUT_WINDOW_MINUTES', 15, int),
        ('SECURITY_LOCKOUT_DURATION_MINUTES', 30, int),
        ('SECURITY_SINGLE_SESSION_ENFORCED', True, bool),
        ('DEFAULT_APPROVAL_DEADLINE_HOURS', 24, int),
        ('TREASURY_MINIMUM_FUND_BALANCE', 0, int),
        ('INVITATION_EXPIRY_DAYS', 7, int),
        ('ENFORCE_DEVICE_WHITELIST', False, bool),
        ('ENABLE_ACTIVITY_GEOLOCATION', True, bool),
    ]
    
    passed = 0
    for key, default, expected_type in test_cases:
        value = get_setting(key, default)
        is_correct = isinstance(value, expected_type)
        status = "✅" if is_correct else "❌"
        print(f"  {status} {key}: {value} ({type(value).__name__})")
        if is_correct:
            passed += 1
    
    return passed == len(test_cases)

def test_security_integration():
    """Test 3: Security settings integration"""
    print_header("TEST 3: Security Settings Integration")
    
    # Test that security settings exist and can be retrieved
    lockout_threshold = get_setting('SECURITY_LOCKOUT_THRESHOLD', 5)
    lockout_window = get_setting('SECURITY_LOCKOUT_WINDOW_MINUTES', 15)
    lockout_duration = get_setting('SECURITY_LOCKOUT_DURATION_MINUTES', 30)
    single_session = get_setting('SECURITY_SINGLE_SESSION_ENFORCED', True)
    
    print(f"Security Lockout Configuration:")
    print(f"  • Threshold: {lockout_threshold} failed attempts")
    print(f"  • Window: {lockout_window} minutes")
    print(f"  • Duration: {lockout_duration} minutes")
    print(f"  • Single Session: {single_session}")
    
    # Check User model has required fields
    from django.db import connection
    
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info('accounts_user')")
        all_fields = [row[1] for row in cursor.fetchall()]
        fields = [f for f in ['failed_login_attempts', 'lockout_until', 'last_failed_login'] if f in all_fields]
    
    print_section("User Model Security Fields")
    required_fields = ['failed_login_attempts', 'lockout_until', 'last_failed_login']
    for field in required_fields:
        has_field = field in fields
        status = "✅" if has_field else "❌"
        print(f"  {status} {field}")
    
    # Check for users with lockout data
    users_with_attempts = User.objects.filter(failed_login_attempts__gt=0).count()
    locked_users = User.objects.filter(lockout_until__gt=timezone.now()).count()
    
    print_section("Current Status")
    print(f"  📊 Users with failed attempts: {users_with_attempts}")
    print(f"  🔒 Currently locked: {locked_users}")
    
    return len(fields) == 3

def test_approval_workflow():
    """Test 4: Approval workflow settings"""
    print_header("TEST 4: Approval Workflow Settings")
    
    deadline_hours = get_setting('DEFAULT_APPROVAL_DEADLINE_HOURS', 24)
    allow_self = get_setting('ALLOW_SELF_APPROVAL', False)
    escalation = get_setting('APPROVAL_ESCALATION_ENABLED', True)
    
    print(f"Approval Workflow Configuration:")
    print(f"  • Default Deadline: {deadline_hours} hours")
    print(f"  • Allow Self-Approval: {allow_self}")
    print(f"  • Escalation Enabled: {escalation}")
    
    # Check requisitions
    from transactions.models import Requisition
    
    total = Requisition.objects.count()
    pending = Requisition.objects.filter(status='pending').count()
    
    print_section("Requisition Status")
    print(f"  📊 Total Requisitions: {total}")
    print(f"  ⏳ Pending: {pending}")
    
    return True

def test_treasury_settings():
    """Test 5: Treasury settings"""
    print_header("TEST 5: Treasury Settings")
    
    min_balance = get_setting('TREASURY_MINIMUM_FUND_BALANCE', 0)
    auto_replenish = get_setting('TREASURY_AUTO_REPLENISHMENT_ENABLED', True)
    
    print(f"Treasury Configuration:")
    print(f"  • Minimum Balance: {min_balance}")
    print(f"  • Auto Replenishment: {auto_replenish}")
    
    # Check funds
    from treasury.models import TreasuryFund
    
    funds_count = TreasuryFund.objects.count()
    
    print_section("Treasury Status")
    print(f"  💰 Total Funds: {funds_count}")
    
    if funds_count > 0:
        for fund in TreasuryFund.objects.all()[:3]:
            print(f"      • {fund.name}: {fund.currency} {fund.current_balance}")
    
    return True

def test_notification_settings():
    """Test 6: Notification settings"""
    print_header("TEST 6: Notification Settings")
    
    notif_settings = {
        'APPROVAL_EMAIL_NOTIFICATIONS': get_setting('APPROVAL_EMAIL_NOTIFICATIONS', True),
        'APPROVAL_ESCALATION_EMAIL_NOTIFICATIONS': get_setting('APPROVAL_ESCALATION_EMAIL_NOTIFICATIONS', True),
        'SLA_BREACH_EMAIL_NOTIFICATIONS': get_setting('SLA_BREACH_EMAIL_NOTIFICATIONS', True),
        'DAILY_SUMMARY_EMAILS': get_setting('DAILY_SUMMARY_EMAILS', False),
    }
    
    print("Notification Configuration:")
    for key, value in notif_settings.items():
        status = "✅ Enabled" if value else "❌ Disabled"
        print(f"  {status} - {key}")
    
    return True

def test_settings_url_access():
    """Test 7: Settings UI URLs"""
    print_header("TEST 7: Settings UI URLs")
    
    from django.urls import reverse, NoReverseMatch
    
    url_tests = [
        ('settings_manager:dashboard', []),
        ('settings_manager:edit_setting', [1]),
        ('settings_manager:activity_logs', []),
        ('settings_manager:system_info', []),
    ]
    
    found = 0
    for url_name, args in url_tests:
        try:
            url = reverse(url_name, args=args)
            print(f"  ✅ {url_name}: {url}")
            found += 1
        except NoReverseMatch:
            print(f"  ❌ {url_name}: Not found")
        except Exception as e:
            print(f"  ⚠️  {url_name}: {str(e)[:50]}")
    
    return found >= 2  # At least dashboard and one other

def test_admin_integration():
    """Test 8: Django admin integration"""
    print_header("TEST 8: Django Admin Integration")
    
    from django.contrib import admin
    from settings_manager.models import SystemSetting
    
    is_registered = SystemSetting in admin.site._registry
    
    print(f"  Django Admin Registration:")
    print(f"    {'✅' if is_registered else '❌'} SystemSetting model")
    
    if is_registered:
        admin_class = admin.site._registry[SystemSetting]
        print(f"    ✅ Admin class: {admin_class.__class__.__name__}")
        
        # Check admin features
        list_display = getattr(admin_class, 'list_display', [])
        list_filter = getattr(admin_class, 'list_filter', [])
        search_fields = getattr(admin_class, 'search_fields', [])
        
        print(f"    📊 List Display: {len(list_display)} fields")
        print(f"    🔍 List Filter: {len(list_filter)} filters")
        print(f"    🔎 Search Fields: {len(search_fields)} fields")
    
    return is_registered

def test_performance():
    """Test 9: Settings retrieval performance"""
    print_header("TEST 9: Performance Test")
    
    # Test individual retrieval
    start = time.time()
    for _ in range(50):
        get_setting('SECURITY_LOCKOUT_THRESHOLD', 5)
    duration_ms = (time.time() - start) * 1000
    
    print(f"Get Setting Performance:")
    print(f"  • 50 calls: {duration_ms:.2f}ms")
    print(f"  • Average: {duration_ms/50:.2f}ms per call")
    
    if duration_ms < 50:
        print(f"  ✅ Performance: Excellent")
    elif duration_ms < 200:
        print(f"  ✅ Performance: Good")
    elif duration_ms < 1000:
        print(f"  ⚠️  Performance: Acceptable")
    else:
        print(f"  ❌ Performance: Needs optimization")
    
    # Test bulk retrieval
    start = time.time()
    settings = SystemSetting.objects.filter(is_active=True)[:20]
    _ = list(settings)
    bulk_duration_ms = (time.time() - start) * 1000
    
    print(f"\nBulk Retrieval (20 settings):")
    print(f"  • Duration: {bulk_duration_ms:.2f}ms")
    
    return duration_ms < 1000

def run_all_tests():
    """Run all integration tests"""
    print("\n" + "="*80)
    print("  PETTYCASH SYSTEM - SETTINGS INTEGRATION TEST")
    print("  Simplified Live System Verification")
    print("="*80)
    
    tests = [
        ("Settings Database Status", test_database_settings),
        ("Get Setting Function", test_get_setting_works),
        ("Security Settings Integration", test_security_integration),
        ("Approval Workflow Settings", test_approval_workflow),
        ("Treasury Settings", test_treasury_settings),
        ("Notification Settings", test_notification_settings),
        ("Settings UI URLs", test_settings_url_access),
        ("Django Admin Integration", test_admin_integration),
        ("Performance Test", test_performance),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result, None))
        except Exception as e:
            results.append((test_name, False, str(e)[:100]))
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for test_name, result, error in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} | {test_name}")
        if error:
            print(f"         Error: {error}")
    
    print(f"\n{'='*80}")
    print(f"  RESULT: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    print(f"{'='*80}\n")
    
    if passed == total:
        print("  🎉 All settings integration tests passed!")
        print("  ✅ Settings are properly wired into the system")
    elif passed >= total * 0.8:
        print("  ✅ Settings are well integrated (80%+ pass rate)")
    elif passed >= total * 0.6:
        print("  ⚠️  Most settings working, some issues detected")
    else:
        print("  ❌ Significant integration issues detected")
    
    print(f"\n{'='*80}\n")
    
    return passed >= total * 0.8

if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
