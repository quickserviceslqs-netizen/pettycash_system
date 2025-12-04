"""
Create timeout/duration settings to replace hardcoded values
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
django.setup()

from settings_manager.models import SystemSetting

timeout_settings = [
    {
        'key': 'PAYMENT_EXECUTION_TIMEOUT_MINUTES',
        'display_name': 'Payment Execution Timeout (Minutes)',
        'value': '60',
        'default_value': '60',
        'setting_type': 'integer',
        'category': 'treasury',
        'description': 'Maximum minutes allowed for payment execution before triggering timeout alert',
        'editable_by_admin': True
    },
    {
        'key': 'PAYMENT_OTP_EXPIRY_MINUTES',
        'display_name': 'Payment OTP Expiry (Minutes)',
        'value': '5',
        'default_value': '5',
        'setting_type': 'integer',
        'category': 'security',
        'description': 'Number of minutes before OTP expires for payment authentication',
        'editable_by_admin': True
    },
    {
        'key': 'VARIANCE_APPROVAL_DEADLINE_HOURS',
        'display_name': 'Variance Approval Deadline (Hours)',
        'value': '24',
        'default_value': '24',
        'setting_type': 'integer',
        'category': 'treasury',
        'description': 'Maximum hours before variance approval request triggers timeout alert',
        'editable_by_admin': True
    },
    {
        'key': 'MAINTENANCE_WINDOW_DURATION_MINUTES',
        'display_name': 'Maintenance Window Duration (Minutes)',
        'value': '30',
        'default_value': '30',
        'setting_type': 'integer',
        'category': 'general',
        'description': 'Default duration in minutes for maintenance windows',
        'editable_by_admin': True
    },
    {
        'key': 'TREASURY_FORECAST_HORIZON_DAYS',
        'display_name': 'Treasury Forecast Horizon (Days)',
        'value': '30',
        'default_value': '30',
        'setting_type': 'integer',
        'category': 'treasury',
        'description': 'Number of days to forecast ahead for treasury projections',
        'editable_by_admin': True
    },
    {
        'key': 'TREASURY_HISTORY_LOOKBACK_DAYS',
        'display_name': 'Treasury History Lookback (Days)',
        'value': '30',
        'default_value': '30',
        'setting_type': 'integer',
        'category': 'treasury',
        'description': 'Number of days to look back for historical treasury analysis',
        'editable_by_admin': True
    },
]

print("Creating timeout/duration settings...")
print("=" * 70)

created = 0
updated = 0
skipped = 0

for setting_data in timeout_settings:
    setting, created_flag = SystemSetting.objects.update_or_create(
        key=setting_data['key'],
        defaults={
            'display_name': setting_data['display_name'],
            'value': setting_data['value'],
            'default_value': setting_data['default_value'],
            'setting_type': setting_data['setting_type'],
            'category': setting_data['category'],
            'description': setting_data['description'],
            'editable_by_admin': setting_data['editable_by_admin']
        }
    )
    
    if created_flag:
        print(f"✅ CREATED: {setting_data['key']}")
        print(f"   Display: {setting_data['display_name']}")
        print(f"   Category: {setting_data['category']}")
        print(f"   Default: {setting_data['value']}")
        created += 1
    else:
        print(f"⚠️  UPDATED: {setting_data['key']}")
        print(f"   Category: {setting_data['category']}")
        print(f"   Value: {setting_data['value']}")
        updated += 1

print("=" * 70)
print(f"Summary: {created} created, {updated} updated")
print(f"\nTotal timeout settings in database: {SystemSetting.objects.filter(key__in=[s['key'] for s in timeout_settings]).count()}")
