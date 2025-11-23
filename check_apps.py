import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
django.setup()

from accounts.models import App

apps = App.objects.all()
print(f'Existing apps: {list(apps.values_list("name", flat=True))}')
print(f'Total count: {apps.count()}')
