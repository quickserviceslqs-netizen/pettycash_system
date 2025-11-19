"""
Test data fixtures for UAT/Testing environment
Load sample data for testing workflows
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import User
from organization.models import Company, Region, Branch, Department
from workflow.models import ApprovalThreshold
from decimal import Decimal


class Command(BaseCommand):
    help = 'Load test data for UAT environment'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Loading test data...')

        # Create test company
        company, _ = Company.objects.get_or_create(
            name='Test Company Ltd',
            defaults={
                'code': 'TEST001',
                'is_active': True
            }
        )

        # Create test region
        region, _ = Region.objects.get_or_create(
            name='Test Region',
            company=company,
            defaults={
                'code': 'TR001',
                'is_active': True
            }
        )

        # Create test branch
        branch, _ = Branch.objects.get_or_create(
            name='Test Branch',
            region=region,
            defaults={
                'is_active': True
            }
        )

        # Create test departments
        finance_dept, _ = Department.objects.get_or_create(
            name='Finance',
            branch=branch,
            defaults={'is_active': True}
        )

        operations_dept, _ = Department.objects.get_or_create(
            name='Operations',
            branch=branch,
            defaults={'is_active': True}
        )

        # Create test users
        users_data = [
            {
                'username': 'treasury_user',
                'email': 'treasury@test.com',
                'first_name': 'Treasury',
                'last_name': 'Manager',
                'role': 'TREASURY',
                'department': finance_dept
            },
            {
                'username': 'finance_user',
                'email': 'finance@test.com',
                'first_name': 'Finance',
                'last_name': 'Officer',
                'role': 'FINANCE',
                'department': finance_dept
            },
            {
                'username': 'branch_user',
                'email': 'branch@test.com',
                'first_name': 'Branch',
                'last_name': 'Manager',
                'role': 'BRANCH_MANAGER',
                'department': operations_dept
            },
            {
                'username': 'staff_user',
                'email': 'staff@test.com',
                'first_name': 'Staff',
                'last_name': 'Member',
                'role': 'STAFF',
                'department': operations_dept
            }
        ]

        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'role': user_data['role'],
                    'department': user_data['department'],
                    'branch': branch,
                    'is_active': True
                }
            )
            if created:
                user.set_password('Test@123456')  # Default test password
                user.save()
                self.stdout.write(f'✅ Created user: {user.username}')

        # Create test approval thresholds
        ApprovalThreshold.objects.get_or_create(
            name='Tier 1 - Small Amounts',
            defaults={
                'origin_type': 'ANY',
                'min_amount': Decimal('0.00'),
                'max_amount': Decimal('1000.00'),
                'roles_sequence': ['BRANCH_MANAGER'],
                'allow_urgent_fasttrack': True,
                'requires_cfo': False,
                'priority': 1,
                'is_active': True
            }
        )

        ApprovalThreshold.objects.get_or_create(
            name='Tier 2 - Medium Amounts',
            defaults={
                'origin_type': 'ANY',
                'min_amount': Decimal('1000.01'),
                'max_amount': Decimal('10000.00'),
                'roles_sequence': ['BRANCH_MANAGER', 'FINANCE'],
                'allow_urgent_fasttrack': True,
                'requires_cfo': False,
                'priority': 2,
                'is_active': True
            }
        )

        ApprovalThreshold.objects.get_or_create(
            name='Tier 3 - Large Amounts',
            defaults={
                'origin_type': 'ANY',
                'min_amount': Decimal('10000.01'),
                'max_amount': Decimal('50000.00'),
                'roles_sequence': ['BRANCH_MANAGER', 'FINANCE', 'TREASURY'],
                'allow_urgent_fasttrack': False,
                'requires_cfo': False,
                'priority': 3,
                'is_active': True
            }
        )

        self.stdout.write(self.style.SUCCESS('✅ Test data loaded successfully!'))
        self.stdout.write('')
        self.stdout.write('Test Users Created:')
        self.stdout.write('  Username: admin | Password: Admin@123456 (superuser)')
        self.stdout.write('  Username: treasury_user | Password: Test@123456')
        self.stdout.write('  Username: finance_user | Password: Test@123456')
        self.stdout.write('  Username: branch_user | Password: Test@123456')
        self.stdout.write('  Username: staff_user | Password: Test@123456')
