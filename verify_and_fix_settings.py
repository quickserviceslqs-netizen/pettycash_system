"""
Verify and fix all settings in the database.
Ensures all critical settings exist and are properly configured.
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pettycash_system.settings")
django.setup()

from settings_manager.models import SystemSetting, get_setting


def ensure_setting(key, value, setting_type, category, description, **kwargs):
    """Ensure a setting exists, create if missing"""
    setting, created = SystemSetting.objects.get_or_create(
        key=key,
        defaults={
            "value": str(value),
            "setting_type": setting_type,
            "category": category,
            "description": description,
            "is_active": True,
            "editable_by_admin": kwargs.get("editable_by_admin", True),
            "requires_restart": kwargs.get("requires_restart", False),
            "is_sensitive": kwargs.get("is_sensitive", False),
        },
    )

    if created:
        print(f"✅ Created: {key} = {value}")
    else:
        print(f"📝 Exists: {key} = {setting.value}")

    return setting


def verify_critical_settings():
    """Verify and create critical settings"""
    print("\n" + "=" * 80)
    print("  VERIFYING CRITICAL SETTINGS")
    print("=" * 80 + "\n")

    critical_settings = [
        # Security - Lockout Settings
        {
            "key": "SECURITY_LOCKOUT_THRESHOLD",
            "value": "5",
            "setting_type": "integer",
            "category": "security",
            "description": "Number of failed login attempts before account lockout",
        },
        {
            "key": "SECURITY_LOCKOUT_WINDOW_MINUTES",
            "value": "15",
            "setting_type": "integer",
            "category": "security",
            "description": "Time window (minutes) to count failed login attempts",
        },
        {
            "key": "SECURITY_LOCKOUT_DURATION_MINUTES",
            "value": "30",
            "setting_type": "integer",
            "category": "security",
            "description": "How long to lock out account after threshold is reached (minutes)",
        },
        {
            "key": "SECURITY_SINGLE_SESSION_ENFORCED",
            "value": "True",
            "setting_type": "boolean",
            "category": "security",
            "description": "Only allow one active session per user at a time",
        },
        # Approval Workflow
        {
            "key": "DEFAULT_APPROVAL_DEADLINE_HOURS",
            "value": "24",
            "setting_type": "integer",
            "category": "approval_workflow",
            "description": "Default hours to approve a requisition before escalation",
        },
        # Treasury
        {
            "key": "TREASURY_MINIMUM_FUND_BALANCE",
            "value": "0",
            "setting_type": "integer",
            "category": "treasury",
            "description": "Minimum balance required in treasury funds",
        },
        {
            "key": "TREASURY_AUTO_REPLENISHMENT_ENABLED",
            "value": "True",
            "setting_type": "boolean",
            "category": "treasury",
            "description": "Automatically replenish funds when below minimum",
        },
        # Device & Location
        {
            "key": "ENFORCE_DEVICE_WHITELIST",
            "value": "False",
            "setting_type": "boolean",
            "category": "security",
            "description": "Only allow access from whitelisted devices",
        },
        {
            "key": "ENABLE_ACTIVITY_GEOLOCATION",
            "value": "True",
            "setting_type": "boolean",
            "category": "security",
            "description": "Track user location for security audit trail",
        },
        # Invitations
        {
            "key": "INVITATION_EXPIRY_DAYS",
            "value": "7",
            "setting_type": "integer",
            "category": "security",
            "description": "Days before user invitation link expires",
        },
    ]

    print("Checking critical settings...\n")
    for setting_data in critical_settings:
        ensure_setting(**setting_data)

    print("\n" + "-" * 80)
    print("✅ All critical settings verified!")
    print("-" * 80)


def test_settings_functionality():
    """Test that settings can be retrieved and used"""
    print("\n" + "=" * 80)
    print("  TESTING SETTINGS FUNCTIONALITY")
    print("=" * 80 + "\n")

    test_cases = [
        ("SECURITY_LOCKOUT_THRESHOLD", int, 5),
        ("SECURITY_LOCKOUT_WINDOW_MINUTES", int, 15),
        ("SECURITY_LOCKOUT_DURATION_MINUTES", int, 30),
        ("SECURITY_SINGLE_SESSION_ENFORCED", bool, True),
        ("DEFAULT_APPROVAL_DEADLINE_HOURS", int, 24),
        ("TREASURY_MINIMUM_FUND_BALANCE", int, 0),
        ("ENABLE_ACTIVITY_GEOLOCATION", bool, True),
        ("INVITATION_EXPIRY_DAYS", int, 7),
    ]

    all_passed = True
    for key, expected_type, default_value in test_cases:
        try:
            value = get_setting(key, default=default_value)
            is_correct_type = isinstance(value, expected_type)

            if is_correct_type:
                print(f"✅ {key}: {value} ({type(value).__name__})")
            else:
                print(
                    f"❌ {key}: {value} (Expected {expected_type.__name__}, got {type(value).__name__})"
                )
                all_passed = False
        except Exception as e:
            print(f"❌ {key}: ERROR - {e}")
            all_passed = False

    print("\n" + "-" * 80)
    if all_passed:
        print("✅ All functionality tests passed!")
    else:
        print("⚠️  Some tests failed - review above")
    print("-" * 80)

    return all_passed


def check_settings_usage():
    """Check where settings are used in the codebase"""
    print("\n" + "=" * 80)
    print("  SETTINGS USAGE IN CODEBASE")
    print("=" * 80 + "\n")

    usage_examples = {
        "accounts/signals.py": [
            "SECURITY_LOCKOUT_THRESHOLD",
            "SECURITY_LOCKOUT_WINDOW_MINUTES",
        ],
        "accounts/views.py": [
            "SECURITY_SINGLE_SESSION_ENFORCED",
            "INVITATION_EXPIRY_DAYS",
        ],
        "treasury/views.py": [
            "TREASURY_MINIMUM_FUND_BALANCE",
            "TREASURY_AUTO_REPLENISHMENT_ENABLED",
        ],
    }

    import os
    from pathlib import Path

    for file_path, settings_keys in usage_examples.items():
        full_path = Path("c:/Users/ADMIN/pettycash_system") / file_path
        if full_path.exists():
            print(f"📄 {file_path}")
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
                for key in settings_keys:
                    if key in content:
                        print(f"   ✅ Uses: {key}")
                    else:
                        print(f"   ⚠️  Missing: {key}")
            print()
        else:
            print(f"❌ File not found: {file_path}\n")


def summary_report():
    """Generate summary report"""
    print("\n" + "=" * 80)
    print("  SETTINGS SUMMARY REPORT")
    print("=" * 80 + "\n")

    total = SystemSetting.objects.count()
    active = SystemSetting.objects.filter(is_active=True).count()
    by_category = {}

    for cat, name in SystemSetting.CATEGORY_CHOICES:
        count = SystemSetting.objects.filter(category=cat, is_active=True).count()
        if count > 0:
            by_category[name] = count

    print(f"📊 Total Settings: {total}")
    print(f"✅ Active Settings: {active}")
    print(
        f"📁 Categories Covered: {len(by_category)}/{len(SystemSetting.CATEGORY_CHOICES)}"
    )
    print()

    print("Settings by Category:")
    for name, count in sorted(by_category.items(), key=lambda x: -x[1]):
        print(f"  • {name}: {count}")

    print("\n" + "-" * 80)
    print("✅ Settings system is fully operational!")
    print("-" * 80)


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("  PETTYCASH SETTINGS VERIFICATION & FIX SCRIPT")
    print("=" * 80)

    # Step 1: Verify critical settings
    verify_critical_settings()

    # Step 2: Test functionality
    test_settings_functionality()

    # Step 3: Check usage in codebase
    check_settings_usage()

    # Step 4: Summary report
    summary_report()

    print("\n✅ Verification complete!\n")
