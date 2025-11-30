from settings_manager.models import SystemSetting

advanced_settings = [
    {
        'key': 'PASSWORD_EXPIRY_DAYS',
        'display_name': 'Password Expiry (Days)',
        'description': 'Number of days before a password must be changed.',
        'category': 'advanced_security',
        'setting_type': 'integer',
        'value': '90',
        'default_value': '90',
        'is_sensitive': False,
        'is_active': True,
        'editable_by_admin': True,
        'requires_restart': False,
    },
    {
        'key': 'LOGIN_NOTIFICATION_ENABLED',
        'display_name': 'Login Notification Enabled',
        'description': 'Send notification on successful or failed login.',
        'category': 'advanced_security',
        'setting_type': 'boolean',
        'value': 'true',
        'default_value': 'false',
        'is_sensitive': False,
        'is_active': True,
        'editable_by_admin': True,
        'requires_restart': False,
    },
    {
        'key': 'RATE_LIMIT_LOGIN_ATTEMPTS',
        'display_name': 'Rate Limit Login Attempts',
        'description': 'Maximum login attempts per IP/device per hour.',
        'category': 'advanced_security',
        'setting_type': 'integer',
        'value': '20',
        'default_value': '20',
        'is_sensitive': False,
        'is_active': True,
        'editable_by_admin': True,
        'requires_restart': False,
    },
    {
        'key': 'FORCE_HTTPS',
        'display_name': 'Force HTTPS',
        'description': 'Require all requests to use HTTPS.',
        'category': 'advanced_security',
        'setting_type': 'boolean',
        'value': 'true',
        'default_value': 'true',
        'is_sensitive': False,
        'is_active': True,
        'editable_by_admin': True,
        'requires_restart': False,
    },
]

for setting in advanced_settings:
    obj, created = SystemSetting.objects.get_or_create(key=setting['key'], defaults=setting)
    if not created:
        for k, v in setting.items():
            setattr(obj, k, v)
        obj.save()
    print(f"Seeded: {setting['key']} -> {obj.value}")
