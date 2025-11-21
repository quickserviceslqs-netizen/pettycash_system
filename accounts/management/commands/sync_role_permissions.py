"""
Management command to sync role-based permissions.
Usage: python manage.py sync_role_permissions
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from accounts.models import User


class Command(BaseCommand):
    help = 'Sync role-based groups and permissions based on ROLE_ACCESS mapping'

    def handle(self, *args, **options):
        from accounts.views import ROLE_ACCESS, APPROVER_ROLES
        
        self.stdout.write(self.style.SUCCESS('\n=== Syncing Role-Based Permissions ===\n'))
        
        # Get content types for permission assignment
        user_ct = ContentType.objects.get_for_model(User)
        
        role_groups = {}
        for role_key, role_display in User.ROLE_CHOICES:
            # Create or get group for each role
            group_name = f"Role: {role_display}"
            group, created = Group.objects.get_or_create(name=group_name)
            role_groups[role_key] = group
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created group: {group_name}'))
            else:
                self.stdout.write(f'  - Group exists: {group_name}')
            
            # Clear existing permissions
            group.permissions.clear()
            
            # Add permissions based on app access
            apps = ROLE_ACCESS.get(role_key, [])
            perm_count = 0
            
            for app in apps:
                # Grant view permissions for accessible apps
                if app == 'transactions':
                    perms = Permission.objects.filter(
                        content_type__app_label='transactions'
                    )
                    group.permissions.add(*perms)
                    perm_count += perms.count()
                
                elif app == 'treasury':
                    perms = Permission.objects.filter(
                        content_type__app_label='treasury'
                    )
                    group.permissions.add(*perms)
                    perm_count += perms.count()
                
                elif app == 'workflow':
                    perms = Permission.objects.filter(
                        content_type__app_label='workflow'
                    )
                    group.permissions.add(*perms)
                    perm_count += perms.count()
                
                elif app == 'reports':
                    perms = Permission.objects.filter(
                        content_type__app_label='reports'
                    )
                    group.permissions.add(*perms)
                    perm_count += perms.count()
            
            # Add approval permission if role is an approver
            if role_key in APPROVER_ROLES:
                self.stdout.write(f'    → Approver role (can approve requisitions)')
            
            self.stdout.write(f'    → Accessible apps: {", ".join(apps) if apps else "None"}')
            self.stdout.write(f'    → Permissions assigned: {perm_count}\n')
        
        # Assign users to their role groups
        self.stdout.write(self.style.SUCCESS('\n=== Assigning Users to Role Groups ===\n'))
        
        for user in User.objects.all():
            user.groups.clear()
            role_group = role_groups.get(user.role)
            if role_group:
                user.groups.add(role_group)
                self.stdout.write(f'  ✓ {user.username} → {role_group.name}')
        
        self.stdout.write(self.style.SUCCESS('\n=== Sync Complete ===\n'))
        self.stdout.write(f'Total groups: {len(role_groups)}')
        self.stdout.write(f'Total users assigned: {User.objects.count()}\n')
