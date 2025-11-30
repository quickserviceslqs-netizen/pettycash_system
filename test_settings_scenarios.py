#!/usr/bin/env python
"""
Comprehensive System Settings Scenario Testing
Tests each category and various scenarios to ensure full functionality
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
django.setup()

from settings_manager.models import SystemSetting
from django.test import Client
from django.contrib.auth import get_user_model
from django.db.models import Q

def run_scenario_tests():
    print('=== COMPREHENSIVE SYSTEM SETTINGS SCENARIO TESTING ===')
    print()

    # Setup test client and admin user
    User = get_user_model()
    client = Client()
    admin_user, _ = User.objects.get_or_create(
        username='test_admin',
        defaults={
            'email': 'admin@test.com',
            'is_superuser': True,
            'is_staff': True,
            'role': 'admin'
        }
    )
    admin_user.set_password('testpass123')
    admin_user.save()
    client.login(username='test_admin', password='testpass123')

    # Test scenarios for each category
    categories = {
        'email': {'name': 'Email Configuration', 'expected_count': 3, 'test_setting': 'EMAIL_HOST'},
        'approval': {'name': 'Approval Workflow', 'expected_count': 5, 'test_setting': 'DEFAULT_APPROVAL_DEADLINE_HOURS'},
        'payment': {'name': 'Payment Settings', 'expected_count': 5, 'test_setting': 'PAYMENT_PROCESSING_FEE'},
        'security': {'name': 'Security & Auth', 'expected_count': 32, 'attention_count': 7, 'test_setting': 'SESSION_TIMEOUT_MINUTES'},
        'notifications': {'name': 'Notifications', 'expected_count': 4, 'test_setting': 'EMAIL_NOTIFICATIONS_ENABLED'},
        'general': {'name': 'General Settings', 'expected_count': 13, 'test_setting': 'APP_VERSION'},
        'reporting': {'name': 'Reports & Analytics', 'expected_count': 5, 'test_setting': 'REPORT_RETENTION_DAYS'},
        'requisition': {'name': 'Requisition Mgmt', 'expected_count': 7, 'test_setting': 'AUTO_APPROVE_BELOW_AMOUNT'},
        'treasury': {'name': 'Treasury Operations', 'expected_count': 15, 'test_setting': 'TREASURY_APPROVAL_THRESHOLD'},
        'workflow': {'name': 'Workflow Automation', 'expected_count': 15, 'test_setting': 'AUTO_ESCALATION_HOURS'},
        'organization': {'name': 'Users & Organization', 'expected_count': 15, 'test_setting': 'DEFAULT_USER_ROLE'}
    }

    all_scenarios_passed = True

    for category_key, category_info in categories.items():
        print(f'🧪 Testing {category_info["name"]} Category')
        print(f'   Expected settings: {category_info["expected_count"]}')

        # Scenario 1: Category filtering
        response = client.get(f'/settings/?category={category_key}')
        if response.status_code != 200:
            print(f'   ❌ Failed to load category page (status: {response.status_code})')
            all_scenarios_passed = False
            continue

        content = response.content.decode()
        table_rows = content.count('<tr>') - 1  # Subtract header row

        if table_rows == category_info['expected_count']:
            print(f'   ✅ Category filtering: {table_rows} settings displayed')
        else:
            print(f'   ❌ Category filtering: {table_rows} settings (expected {category_info["expected_count"]})')
            all_scenarios_passed = False

        # Scenario 2: Settings belong to correct category
        db_settings = SystemSetting.objects.filter(category=category_key)
        if db_settings.count() == category_info['expected_count']:
            print(f'   ✅ Database verification: {db_settings.count()} settings in database')
        else:
            print(f'   ❌ Database mismatch: {db_settings.count()} in DB (expected {category_info["expected_count"]})')
            all_scenarios_passed = False

        # Scenario 3: Test specific setting exists and is editable
        if 'test_setting' in category_info:
            test_setting = SystemSetting.objects.filter(key=category_info['test_setting']).first()
            if test_setting:
                print(f'   ✅ Test setting found: {test_setting.key} ({test_setting.display_name})')

                # Test edit page access
                edit_response = client.get(f'/settings/edit/{test_setting.id}/')
                if edit_response.status_code == 200:
                    print(f'   ✅ Edit page accessible for {test_setting.key}')
                else:
                    print(f'   ❌ Edit page failed for {test_setting.key} (status: {edit_response.status_code})')
                    all_scenarios_passed = False
            else:
                print(f'   ❌ Test setting not found: {category_info["test_setting"]}')
                all_scenarios_passed = False

        # Special scenario for security category
        if category_key == 'security' and 'attention_count' in category_info:
            attention_settings = SystemSetting.objects.filter(category='security').filter(
                Q(is_active=False) | Q(setting_type='boolean', value__in=['false', 'False']) | Q(value__in=['', None])
            )
            if attention_settings.count() == category_info['attention_count']:
                print(f'   ✅ Security attention filter: {attention_settings.count()} settings need attention')
            else:
                print(f'   ❌ Security attention filter: {attention_settings.count()} (expected {category_info["attention_count"]})')
                all_scenarios_passed = False

        print()

    # Scenario 4: Cross-category search
    print('🧪 Testing Cross-Category Search Scenarios')
    search_term = 'APPROVAL'
    response = client.get(f'/settings/?search={search_term}')
    if response.status_code == 200:
        content = response.content.decode()
        if search_term in content:
            search_results = content.count('<tr>') - 1
            print(f'   ✅ Search for "{search_term}": {search_results} results found')
        else:
            print(f'   ❌ Search for "{search_term}": No results found')
            all_scenarios_passed = False
    else:
        print(f'   ❌ Search request failed (status: {response.status_code})')
        all_scenarios_passed = False

    # Scenario 5: Main dashboard stats
    print()
    print('🧪 Testing Main Dashboard Stats')
    response = client.get('/settings/')
    if response.status_code == 200:
        content = response.content.decode()

        # Check total settings
        total_settings = SystemSetting.objects.filter(is_active=True).count()
        if str(total_settings) in content:
            print(f'   ✅ Total active settings: {total_settings}')
        else:
            print(f'   ❌ Total active settings count mismatch')
            all_scenarios_passed = False

        # Check categories count
        if '11' in content:  # Should show 11 categories
            print(f'   ✅ Categories count: 11')
        else:
            print(f'   ❌ Categories count not found')
            all_scenarios_passed = False
    else:
        print(f'   ❌ Main dashboard failed to load (status: {response.status_code})')
        all_scenarios_passed = False

    print()
    print('=== SCENARIO TESTING COMPLETE ===')
    if all_scenarios_passed:
        print('🎉 ALL SCENARIOS PASSED - System Settings fully operational!')
        return True
    else:
        print('⚠️  Some scenarios failed - Review issues above')
        return False

if __name__ == '__main__':
    success = run_scenario_tests()
    sys.exit(0 if success else 1)