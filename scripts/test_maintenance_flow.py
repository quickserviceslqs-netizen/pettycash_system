import os
import django
import sys
import pathlib

# Ensure project root is on sys.path so Django settings module can be imported
BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from settings_manager.models import SystemSetting
from system_maintenance.models import MaintenanceMode
from django.utils import timezone

User = get_user_model()

u = User.objects.filter(is_superuser=True).first()
if not u:
    print('NO_SUPERUSER')
    sys.exit(2)

# Ensure SystemSetting exists
setting, created = SystemSetting.objects.get_or_create(
    key='SYSTEM_MAINTENANCE_MODE',
    defaults={
        'display_name': 'System Maintenance Mode',
        'description': 'Toggle basic maintenance mode setting',
        'category': 'general',
        'setting_type': 'boolean',
        'value': 'false',
        'default_value': 'false',
        'is_active': True,
        'editable_by_admin': True,
        'requires_restart': False,
    }
)
print('SETTING_EXISTS', setting.id, 'created=', created)

client = Client()
client.force_login(u)

# 1. GET the maintenance page
r = client.get('/settings/maintenance/')
print('GET maintenance page:', r.status_code)

# 2. Toggle the setting
current = setting.is_active
# Prepare POST to set is_active to opposite
post_data = {'action': 'toggle_setting'}
if not current:
    post_data['is_active'] = 'on'
else:
    # omit is_active to set false
    pass
r = client.post('/settings/maintenance/', post_data, follow=True)
print('POST toggle_setting -> status', r.status_code)
setting.refresh_from_db()
print('New setting.is_active', setting.is_active, 'value', setting.value)

# 3. Create a maintenance session
r = client.post('/settings/maintenance/', {
    'action': 'create_session',
    'reason': 'Automated test session',
    'duration_minutes': '15',
    'notify_users': 'on',
    'custom_message': 'Test maintenance in progress',
}, follow=True)
print('POST create_session ->', r.status_code)
active = MaintenanceMode.objects.filter(is_active=True).first()
print('Active session exists:', bool(active), 'id=', getattr(active, 'id', None))

# 4. Deactivate session if exists
if active:
    r = client.post('/settings/maintenance/', {
        'action': 'deactivate_session',
        'session_id': str(active.id),
        'notes': 'Deactivating from test script',
    }, follow=True)
    print('POST deactivate_session ->', r.status_code)
    active = MaintenanceMode.objects.filter(is_active=True).first()
    print('Active session after deactivate:', bool(active))
else:
    print('No active session to deactivate')

# 5. Sync behavior: set setting to true then sync
setting.is_active = True
setting.value = 'true'
setting.save()
print('Setting set to true for sync test')
r = client.post('/settings/maintenance/', {'action': 'sync_to_session'}, follow=True)
print('POST sync_to_session ->', r.status_code)
active = MaintenanceMode.objects.filter(is_active=True).first()
print('Active session after sync:', bool(active), 'id=', getattr(active, 'id', None))

# Clean up: deactivate any active
for s in MaintenanceMode.objects.filter(is_active=True):
    s.deactivate(u, success=True, notes='Cleanup after test')
print('Cleanup done')
