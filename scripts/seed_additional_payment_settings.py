from settings_manager.models import SystemSetting

additional_payment_settings = [
    {
        'key': 'PAYMENT_METHOD_RESTRICTIONS',
        'display_name': 'Payment Method Restrictions',
        'description': 'Restrict payment methods by amount or role (JSON config).',
        'category': 'payment',
        'setting_type': 'json',
        'value': '{"mpesa": {"max": 100000}, "bank": {"min": 10000}}',
        'default_value': '{"mpesa": {"max": 100000}, "bank": {"min": 10000}}',
        'is_sensitive': False,
        'is_active': True,
        'editable_by_admin': True,
        'requires_restart': False,
    },
    {
        'key': 'PAYMENT_TIME_WINDOW',
        'display_name': 'Payment Time Window',
        'description': 'Allowed payment hours (e.g., 08:00-18:00).',
        'category': 'payment',
        'setting_type': 'string',
        'value': '08:00-18:00',
        'default_value': '08:00-18:00',
        'is_sensitive': False,
        'is_active': True,
        'editable_by_admin': True,
        'requires_restart': False,
    },
    {
        'key': 'PAYMENT_MULTI_APPROVAL_ENABLED',
        'display_name': 'Multi-level Approval Enabled',
        'description': 'Require multiple approvers for high-value payments.',
        'category': 'payment',
        'setting_type': 'boolean',
        'value': 'false',
        'default_value': 'false',
        'is_sensitive': False,
        'is_active': True,
        'editable_by_admin': True,
        'requires_restart': False,
    },
    {
        'key': 'PAYMENT_NOTIFICATION_RECIPIENTS',
        'display_name': 'Payment Notification Recipients',
        'description': 'Comma-separated emails to notify on payment events.',
        'category': 'payment',
        'setting_type': 'string',
        'value': '',
        'default_value': '',
        'is_sensitive': False,
        'is_active': True,
        'editable_by_admin': True,
        'requires_restart': False,
    },
    {
        'key': 'PAYMENT_HOLD_ENABLED',
        'display_name': 'Payment Hold Enabled',
        'description': 'Allow payments to be placed on hold for manual review.',
        'category': 'payment',
        'setting_type': 'boolean',
        'value': 'false',
        'default_value': 'false',
        'is_sensitive': False,
        'is_active': True,
        'editable_by_admin': True,
        'requires_restart': False,
    },
]

for setting in additional_payment_settings:
    obj, created = SystemSetting.objects.get_or_create(key=setting['key'], defaults=setting)
    if not created:
        for k, v in setting.items():
            setattr(obj, k, v)
        obj.save()
    print(f"Seeded: {setting['key']} -> {obj.value}")
