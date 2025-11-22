import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
u = User.objects.get(username='admin')

print(f'Username: {u.username}')
print(f'Is superuser: {u.is_superuser}')
print(f'Is staff: {u.is_staff}')
print(f'Is active: {u.is_active}')
print(f'Has auth.view_user perm: {u.has_perm("auth.view_user")}')
print(f'Has module perms for auth: {u.has_module_perms("auth")}')
