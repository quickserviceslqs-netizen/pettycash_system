#!/usr/bin/env python
"""
One-time script to create superuser
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pettycash_system.settings")
django.setup()

from accounts.models import User

# Create a new fresh superuser
username = "superadmin"
email = "superadmin@pettycash.com"
password = "Super@123456"

# Delete if exists
User.objects.filter(username=username).delete()

# Create new superuser
superuser = User.objects.create_superuser(
    username=username,
    email=email,
    password=password,
    first_name="Super",
    last_name="Admin",
)

print(f"✓ Superuser created successfully!")
print(f"Username: {username}")
print(f"Password: {password}")
print(f"Email: {email}")
print(f"Is superuser: {superuser.is_superuser}")
print(f"Is staff: {superuser.is_staff}")
print(f"Is active: {superuser.is_active}")
