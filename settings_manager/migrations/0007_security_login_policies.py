from django.db import migrations


def seed_security_settings(apps, schema_editor):
    SystemSetting = apps.get_model("settings_manager", "SystemSetting")

    defaults = [
        {
            "key": "SECURITY_LOCKOUT_THRESHOLD",
            "display_name": "Lockout Threshold (failed attempts)",
            "description": "Number of failed login attempts before an account is temporarily locked.",
            "category": "security",
            "setting_type": "integer",
            "value": "5",
            "default_value": "5",
            "is_sensitive": False,
            "editable_by_admin": True,
            "requires_restart": False,
        },
        {
            "key": "SECURITY_LOCKOUT_WINDOW_MINUTES",
            "display_name": "Lockout Window (minutes)",
            "description": "How long an account remains locked after too many failed attempts.",
            "category": "security",
            "setting_type": "integer",
            "value": "15",
            "default_value": "15",
            "is_sensitive": False,
            "editable_by_admin": True,
            "requires_restart": False,
        },
        {
            "key": "SECURITY_SINGLE_SESSION_ENFORCED",
            "display_name": "Enforce Single Session Per User",
            "description": "When enabled, logging in from a new device/browser terminates all other active sessions for that user.",
            "category": "security",
            "setting_type": "boolean",
            "value": "true",
            "default_value": "true",
            "is_sensitive": False,
            "editable_by_admin": True,
            "requires_restart": False,
        },
    ]

    for data in defaults:
        SystemSetting.objects.get_or_create(key=data["key"], defaults=data)


def unseed_security_settings(apps, schema_editor):
    SystemSetting = apps.get_model("settings_manager", "SystemSetting")
    for key in [
        "SECURITY_LOCKOUT_THRESHOLD",
        "SECURITY_LOCKOUT_WINDOW_MINUTES",
        "SECURITY_SINGLE_SESSION_ENFORCED",
    ]:
        try:
            SystemSetting.objects.filter(key=key).delete()
        except Exception:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ("settings_manager", "0006_merge_20251123_1908"),
    ]

    operations = [
        migrations.RunPython(seed_security_settings, unseed_security_settings),
    ]
