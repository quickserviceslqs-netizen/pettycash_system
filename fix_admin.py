import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
django.setup()

from accounts.models import User

# Fix the admin account
try:
    admin = User.objects.get(username='admin')
    admin.is_superuser = True
    admin.is_staff = True
    admin.is_active = True
    admin.set_password('Admin@123456')
    admin.save()
    
    print(f'✓ Admin account restored!')
    print(f'Username: admin')
    print(f'Password: Admin@123456')
    print(f'Is superuser: {admin.is_superuser}')
    print(f'Is staff: {admin.is_staff}')
except User.DoesNotExist:
    print('Admin user not found')

# Also check superadmin
try:
    superadmin = User.objects.get(username='superadmin')
    print(f'\n✓ Superadmin also available!')
    print(f'Username: superadmin')
    print(f'Password: Super@123456')
    print(f'Is superuser: {superadmin.is_superuser}')
except User.DoesNotExist:
    pass

print('\n--- All Superusers in Database ---')
for u in User.objects.filter(is_superuser=True):
    print(f'{u.username} - Active: {u.is_active}, Staff: {u.is_staff}')
