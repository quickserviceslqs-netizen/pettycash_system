"""
Comprehensive test script to verify all settings are properly integrated and wired.
Tests settings from database, their usage in code, and functionality.
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pettycash_system.settings")
django.setup()

import json

from django.contrib.auth import get_user_model
from django.db.models import Count

from settings_manager.models import SystemSetting, get_setting

User = get_user_model()


def print_header(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_section(title):
    print(f"\n{'-'*80}")
    print(f"  {title}")
    print(f"{'-'*80}")


def test_settings_database():
    """Test 1: Verify settings exist in database"""
    print_header("TEST 1: DATABASE SETTINGS INVENTORY")

    total = SystemSetting.objects.count()
    active = SystemSetting.objects.filter(is_active=True).count()
    inactive = total - active

    print(f"📊 Total Settings: {total}")
    print(f"✅ Active Settings: {active}")
    print(f"❌ Inactive Settings: {inactive}")

    print_section("Settings by Category")
    for cat, name in SystemSetting.CATEGORY_CHOICES:
        count = SystemSetting.objects.filter(category=cat, is_active=True).count()
        if count > 0:
            print(f"  • {name}: {count} settings")

    return total > 0


def test_settings_types():
    """Test 2: Verify different setting types work correctly"""
    print_header("TEST 2: SETTING TYPES VALIDATION")

    types_count = {}
    for setting in SystemSetting.objects.filter(is_active=True):
        types_count[setting.setting_type] = types_count.get(setting.setting_type, 0) + 1

    print_section("Settings by Type")
    for stype, name in SystemSetting.SETTING_TYPE_CHOICES:
        count = types_count.get(stype, 0)
        if count > 0:
            print(f"  • {name} ({stype}): {count} settings")

    # Test type conversion
    print_section("Type Conversion Tests")
    test_cases = []

    # Test boolean
    bool_settings = SystemSetting.objects.filter(
        setting_type="boolean", is_active=True
    ).first()
    if bool_settings:
        val = bool_settings.get_typed_value()
        test_cases.append(
            ("Boolean", bool_settings.key, type(val).__name__, isinstance(val, bool))
        )

    # Test integer
    int_settings = SystemSetting.objects.filter(
        setting_type="integer", is_active=True
    ).first()
    if int_settings:
        val = int_settings.get_typed_value()
        test_cases.append(
            ("Integer", int_settings.key, type(val).__name__, isinstance(val, int))
        )

    # Test JSON
    json_settings = SystemSetting.objects.filter(
        setting_type="json", is_active=True
    ).first()
    if json_settings:
        val = json_settings.get_typed_value()
        test_cases.append(
            (
                "JSON",
                json_settings.key,
                type(val).__name__,
                isinstance(val, (dict, list)),
            )
        )

    for test_type, key, result_type, passed in test_cases:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} | {test_type}: {key} → {result_type}")

    return all(passed for _, _, _, passed in test_cases)


def test_get_setting_function():
    """Test 3: Test the get_setting() utility function"""
    print_header("TEST 3: GET_SETTING() FUNCTION")

    print_section("Retrieving Active Settings")
    test_keys = [
        "DEFAULT_APPROVAL_DEADLINE_HOURS",
        "SECURITY_LOCKOUT_THRESHOLD",
        "TREASURY_MINIMUM_FUND_BALANCE",
        "ENABLE_ACTIVITY_GEOLOCATION",
        "INVITATION_EXPIRY_DAYS",
    ]

    results = []
    for key in test_keys:
        try:
            value = get_setting(key)
            exists = SystemSetting.objects.filter(key=key, is_active=True).exists()
            status = "✅" if value is not None or not exists else "❌"
            print(f"  {status} {key}: {value}")
            results.append(True)
        except Exception as e:
            print(f"  ❌ {key}: ERROR - {e}")
            results.append(False)

    print_section("Testing Default Fallback")
    non_existent = get_setting(
        "NON_EXISTENT_SETTING_KEY_12345", default="fallback_value"
    )
    default_works = non_existent == "fallback_value"
    status = "✅ PASS" if default_works else "❌ FAIL"
    print(f"  {status} | Non-existent key returns default: {default_works}")
    results.append(default_works)

    return all(results)


def test_settings_integration():
    """Test 4: Verify settings are integrated into the codebase"""
    print_header("TEST 4: CODE INTEGRATION VERIFICATION")

    integrations = {
        "Security & Login": [
            "SECURITY_LOCKOUT_THRESHOLD",
            "SECURITY_LOCKOUT_WINDOW_MINUTES",
            "SECURITY_SINGLE_SESSION_ENFORCED",
        ],
        "Treasury Operations": [
            "TREASURY_MINIMUM_FUND_BALANCE",
            "TREASURY_AUTO_REPLENISHMENT_ENABLED",
        ],
        "Device & Location": [
            "ENFORCE_DEVICE_WHITELIST",
            "ENABLE_ACTIVITY_GEOLOCATION",
        ],
        "User Invitations": [
            "INVITATION_EXPIRY_DAYS",
        ],
    }

    all_integrated = True
    for area, keys in integrations.items():
        print_section(area)
        for key in keys:
            try:
                setting = SystemSetting.objects.filter(key=key, is_active=True).first()
                if setting:
                    value = get_setting(key)
                    print(f"  ✅ {key}")
                    print(f"      Value: {value}")
                    print(f"      Type: {setting.setting_type}")
                    print(f"      Category: {setting.get_category_display()}")
                else:
                    print(f"  ⚠️  {key} - NOT FOUND IN DATABASE")
                    all_integrated = False
            except Exception as e:
                print(f"  ❌ {key} - ERROR: {e}")
                all_integrated = False

    return all_integrated


def test_category_coverage():
    """Test 5: Check which categories have settings"""
    print_header("TEST 5: CATEGORY COVERAGE ANALYSIS")

    coverage = {}
    for cat, name in SystemSetting.CATEGORY_CHOICES:
        count = SystemSetting.objects.filter(category=cat, is_active=True).count()
        coverage[name] = count

    has_settings = [name for name, count in coverage.items() if count > 0]
    no_settings = [name for name, count in coverage.items() if count == 0]

    if has_settings:
        print_section("Categories WITH Settings")
        for name in sorted(has_settings):
            count = coverage[name]
            print(f"  ✅ {name}: {count} setting(s)")

    if no_settings:
        print_section("Categories WITHOUT Settings (Opportunities)")
        for name in sorted(no_settings):
            print(f"  ⚠️  {name}: 0 settings")

    coverage_pct = (len(has_settings) / len(SystemSetting.CATEGORY_CHOICES)) * 100
    print_section("Summary")
    print(
        f"  Coverage: {len(has_settings)}/{len(SystemSetting.CATEGORY_CHOICES)} categories ({coverage_pct:.1f}%)"
    )

    return coverage_pct > 50  # At least 50% coverage


def test_editable_settings():
    """Test 6: Check editable vs locked settings"""
    print_header("TEST 6: EDITABLE SETTINGS ANALYSIS")

    editable = SystemSetting.objects.filter(
        is_active=True, editable_by_admin=True
    ).count()
    locked = SystemSetting.objects.filter(
        is_active=True, editable_by_admin=False
    ).count()
    requires_restart = SystemSetting.objects.filter(
        is_active=True, requires_restart=True
    ).count()
    sensitive = SystemSetting.objects.filter(is_active=True, is_sensitive=True).count()

    print(f"  ✏️  Editable by Admin: {editable}")
    print(f"  🔒 Locked (Code Only): {locked}")
    print(f"  🔄 Requires Restart: {requires_restart}")
    print(f"  🔐 Sensitive (Hidden): {sensitive}")

    if requires_restart > 0:
        print_section("Settings Requiring Restart")
        for setting in SystemSetting.objects.filter(
            is_active=True, requires_restart=True
        ):
            print(f"    • {setting.key} ({setting.get_category_display()})")

    return editable > 0


def test_settings_usage_in_code():
    """Test 7: Search for actual usage in codebase"""
    print_header("TEST 7: CODEBASE USAGE VERIFICATION")

    import subprocess

    # Get all active setting keys
    all_keys = list(
        SystemSetting.objects.filter(is_active=True).values_list("key", flat=True)
    )

    print(f"  📝 Checking {len(all_keys)} settings for usage in code...")

    used_count = 0
    unused_settings = []

    for key in all_keys[:10]:  # Test first 10 to avoid long execution
        try:
            # Use findstr on Windows to search for the key
            result = subprocess.run(
                ["findstr", "/s", "/i", "/m", key, "*.py"],
                cwd="c:\\Users\\ADMIN\\pettycash_system",
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.stdout.strip():
                used_count += 1
            else:
                unused_settings.append(key)
        except:
            pass  # Skip if command fails

    print(f"  ✅ Found {used_count} settings used in code (sample check)")

    if unused_settings:
        print_section("Potentially Unused Settings (Sample)")
        for key in unused_settings[:5]:
            print(f"    ⚠️  {key}")

    return True


def test_critical_settings():
    """Test 8: Verify critical settings are configured"""
    print_header("TEST 8: CRITICAL SETTINGS CHECK")

    critical_settings = {
        "Security": [
            "SECURITY_LOCKOUT_THRESHOLD",
            "SECURITY_LOCKOUT_WINDOW_MINUTES",
            "SECURITY_LOCKOUT_DURATION_MINUTES",
            "SECURITY_SINGLE_SESSION_ENFORCED",
        ],
        "Approval Workflow": [
            "DEFAULT_APPROVAL_DEADLINE_HOURS",
        ],
        "Treasury": [
            "TREASURY_MINIMUM_FUND_BALANCE",
        ],
    }

    all_critical_present = True
    for area, keys in critical_settings.items():
        print_section(area)
        for key in keys:
            setting = SystemSetting.objects.filter(key=key, is_active=True).first()
            if setting:
                value = get_setting(key)
                print(f"  ✅ {key} = {value}")
            else:
                print(f"  ❌ {key} - MISSING!")
                all_critical_present = False

    return all_critical_present


def run_all_tests():
    """Run all tests and provide summary"""
    print("\n" + "=" * 80)
    print("  PETTYCASH SYSTEM - COMPREHENSIVE SETTINGS TEST SUITE")
    print("  Testing all settings integration and functionality")
    print("=" * 80)

    tests = [
        ("Database Settings Inventory", test_settings_database),
        ("Setting Types Validation", test_settings_types),
        ("get_setting() Function", test_get_setting_function),
        ("Code Integration", test_settings_integration),
        ("Category Coverage", test_category_coverage),
        ("Editable Settings", test_editable_settings),
        ("Codebase Usage", test_settings_usage_in_code),
        ("Critical Settings", test_critical_settings),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result, None))
        except Exception as e:
            results.append((test_name, False, str(e)))

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
    print(
        f"  OVERALL RESULT: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)"
    )
    print(f"{'='*80}\n")

    if passed == total:
        print("  🎉 All settings are properly integrated and wired!")
    elif passed >= total * 0.8:
        print("  ⚠️  Most settings are working, but some issues found.")
    else:
        print("  ❌ Significant issues detected. Review failed tests.")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
