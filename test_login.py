import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
django.setup()

from django.contrib.auth import authenticate

# Test admin login
user = authenticate(username='admin', password='Admin@123456')
if user:
    print('✓ Login test: SUCCESS')
    print(f'User: {user.username}')
    print(f'Is superuser: {user.is_superuser}')
    print(f'Is staff: {user.is_staff}')
    print(f'Is active: {user.is_active}')
else:
    print('✗ Login test: FAILED')

# Test superadmin login
user2 = authenticate(username='superadmin', password='Super@123456')
if user2:
    print('\n✓ Superadmin login: SUCCESS')
    print(f'User: {user2.username}')
    print(f'Is superuser: {user2.is_superuser}')
else:
    print('\n✗ Superadmin login: FAILED')
