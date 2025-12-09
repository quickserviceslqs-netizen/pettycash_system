"""
Create treasury configuration settings
"""

from django.db import migrations


def create_treasury_settings(apps, schema_editor):
    SystemSetting = apps.get_model("settings_manager", "SystemSetting")

    treasury_settings = [
        {
            "key": "TREASURY_DEFAULT_REORDER_LEVEL",
            "display_name": "Default Fund Reorder Level",
            "description": "Default minimum balance threshold for treasury funds. When fund balance falls below this, system alerts for replenishment.",
            "category": "treasury",
            "setting_type": "integer",
            "value": "50000",
            "default_value": "50000",
            "is_sensitive": False,
            "is_active": True,
            "editable_by_admin": True,
            "requires_restart": False,
        },
        {
            "key": "TREASURY_MINIMUM_FUND_BALANCE",
            "display_name": "Minimum Fund Balance",
            "description": "Minimum allowed balance for treasury funds. Prevents fund balance from going below this amount.",
            "category": "treasury",
            "setting_type": "integer",
            "value": "0",
            "default_value": "0",
            "is_sensitive": False,
            "is_active": True,
            "editable_by_admin": True,
            "requires_restart": False,
        },
        {
            "key": "TREASURY_ALLOW_NEGATIVE_BALANCE",
            "display_name": "Allow Negative Fund Balance",
            "description": "Whether treasury funds can have negative balances (overdraft). If disabled, payments will be rejected when insufficient funds.",
            "category": "treasury",
            "setting_type": "boolean",
            "value": "false",
            "default_value": "false",
            "is_sensitive": False,
            "is_active": True,
            "editable_by_admin": True,
            "requires_restart": False,
        },
        {
            "key": "TREASURY_LOW_BALANCE_ALERT_PERCENTAGE",
            "display_name": "Low Balance Alert Percentage",
            "description": "Percentage of reorder level at which to send low balance alerts. E.g., 80 means alert when balance is 80% of reorder level.",
            "category": "treasury",
            "setting_type": "integer",
            "value": "100",
            "default_value": "100",
            "is_sensitive": False,
            "is_active": True,
            "editable_by_admin": True,
            "requires_restart": False,
        },
        {
            "key": "TREASURY_AUTO_REPLENISHMENT_ENABLED",
            "display_name": "Enable Auto Replenishment Requests",
            "description": "Automatically create replenishment requests when fund balance falls below reorder level.",
            "category": "treasury",
            "setting_type": "boolean",
            "value": "true",
            "default_value": "true",
            "is_sensitive": False,
            "is_active": True,
            "editable_by_admin": True,
            "requires_restart": False,
        },
        {
            "key": "TREASURY_DEFAULT_REPLENISHMENT_AMOUNT",
            "display_name": "Default Replenishment Amount",
            "description": "Default amount to replenish when creating manual replenishment requests.",
            "category": "treasury",
            "setting_type": "integer",
            "value": "100000",
            "default_value": "100000",
            "is_sensitive": False,
            "is_active": True,
            "editable_by_admin": True,
            "requires_restart": False,
        },
        {
            "key": "TREASURY_PAYMENT_EXECUTION_TIMEOUT",
            "display_name": "Payment Execution Timeout (seconds)",
            "description": "Maximum time allowed for payment execution before timeout.",
            "category": "treasury",
            "setting_type": "integer",
            "value": "300",
            "default_value": "300",
            "is_sensitive": False,
            "is_active": True,
            "editable_by_admin": True,
            "requires_restart": False,
        },
        {
            "key": "TREASURY_REQUIRE_OTP_FOR_PAYMENTS",
            "display_name": "Require OTP for Payments",
            "description": "Require OTP verification for all payment executions for additional security.",
            "category": "treasury",
            "setting_type": "boolean",
            "value": "false",
            "default_value": "false",
            "is_sensitive": False,
            "is_active": True,
            "editable_by_admin": True,
            "requires_restart": False,
        },
        {
            "key": "TREASURY_OTP_EXPIRY_MINUTES",
            "display_name": "OTP Expiry Time (minutes)",
            "description": "How long OTP codes remain valid for payment verification.",
            "category": "treasury",
            "setting_type": "integer",
            "value": "5",
            "default_value": "5",
            "is_sensitive": False,
            "is_active": True,
            "editable_by_admin": True,
            "requires_restart": False,
        },
        {
            "key": "TREASURY_MAX_PAYMENT_RETRY_ATTEMPTS",
            "display_name": "Maximum Payment Retry Attempts",
            "description": "Maximum number of times a failed payment can be retried.",
            "category": "treasury",
            "setting_type": "integer",
            "value": "3",
            "default_value": "3",
            "is_sensitive": False,
            "is_active": True,
            "editable_by_admin": True,
            "requires_restart": False,
        },
    ]

    for setting_data in treasury_settings:
        SystemSetting.objects.get_or_create(
            key=setting_data["key"], defaults=setting_data
        )


def remove_treasury_settings(apps, schema_editor):
    SystemSetting = apps.get_model("settings_manager", "SystemSetting")
    SystemSetting.objects.filter(category="treasury").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("settings_manager", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_treasury_settings, remove_treasury_settings),
    ]
