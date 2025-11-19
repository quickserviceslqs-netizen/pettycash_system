#!/usr/bin/env python
"""
One-time script to create superuser on Render
Run this once, then delete it
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
django.setup()

from accounts.models import User

# Check if superuser exists
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@pettycash.com',
        password='Admin@123456',  # CHANGE THIS AFTER FIRST LOGIN!
        first_name='System',
        last_name='Administrator'
    )
    print("✅ Superuser 'admin' created successfully!")
    print("⚠️ Default password: Admin@123456")
    print("🔒 CHANGE THIS PASSWORD IMMEDIATELY after first login!")
else:
    print("ℹ️ Superuser 'admin' already exists")
