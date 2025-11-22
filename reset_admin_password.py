import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Get or create admin user
admin, created = User.objects.get_or_create(
    username='admin',
    defaults={
        'email': 'admin@pettycash.com',
        'is_superuser': True,
        'is_staff': True,
        'is_active': True,
    }
)

# Set a simple password
admin.set_password('admin123')
admin.is_active = True
admin.is_superuser = True
admin.is_staff = True
admin.save()

print(f'Admin user {"created" if created else "updated"}')
print(f'Username: {admin.username}')
print(f'Password: admin123')
print(f'Is active: {admin.is_active}')
print(f'Is superuser: {admin.is_superuser}')
print(f'Is staff: {admin.is_staff}')
