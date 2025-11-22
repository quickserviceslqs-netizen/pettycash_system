import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.permissions import get_user_apps

User = get_user_model()
su = User.objects.filter(is_superuser=True).first()

if su:
    print(f'Superuser: {su.username}')
    print(f'Is superuser: {su.is_superuser}')
    apps = get_user_apps(su)
    print(f'Apps for superuser: {apps}')
else:
    print('No superuser found')
