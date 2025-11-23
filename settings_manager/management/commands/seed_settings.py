from django.core.management.base import BaseCommand
from settings_manager.models import SystemSetting


class Command(BaseCommand):
    help = 'Seed default system settings'

    def handle(self, *args, **options):
        settings = [
            {
                'key': 'DEFAULT_CHANGE_REQUEST_DEADLINE_HOURS',
                'display_name': 'Default Change Request Deadline (Hours)',
                'description': 'Default number of hours for requester to respond to change requests',
                'category': 'approval',
                'setting_type': 'integer',
                'value': '48',
                'default_value': '48',
            },
            {
                'key': 'AUTO_REJECT_EXPIRED_CHANGES',
                'display_name': 'Auto-Reject Expired Change Requests',
                'description': 'Automatically reject requisitions when change request deadline expires',
                'category': 'approval',
                'setting_type': 'boolean',
                'value': 'true',
                'default_value': 'true',
            },
            {
                'key': 'APPROVAL_EMAIL_NOTIFICATIONS',
                'display_name': 'Send Email Notifications for Approvals',
                'description': 'Enable/disable email notifications for approval actions',
                'category': 'notifications',
                'setting_type': 'boolean',
                'value': 'true',
                'default_value': 'true',
            },
            {
                'key': 'SYSTEM_EMAIL_FROM',
                'display_name': 'System Email (From Address)',
                'description': 'Email address used for system notifications',
                'category': 'email',
                'setting_type': 'email',
                'value': 'noreply@pettycash.local',
                'default_value': 'noreply@pettycash.local',
            },
            {
                'key': 'MAX_REQUISITION_AMOUNT',
                'display_name': 'Maximum Requisition Amount',
                'description': 'Maximum amount allowed for a single requisition',
                'category': 'approval',
                'setting_type': 'integer',
                'value': '1000000',
                'default_value': '1000000',
            },
            {
                'key': 'ACTIVITY_LOG_RETENTION_DAYS',
                'display_name': 'Activity Log Retention (Days)',
                'description': 'Number of days to keep activity logs before archiving',
                'category': 'security',
                'setting_type': 'integer',
                'value': '90',
                'default_value': '90',
            },
            {
                'key': 'FAST_TRACK_ENABLED',
                'display_name': 'Enable Fast-Track Approvals',
                'description': 'Allow urgent requisitions to skip intermediate approvers',
                'category': 'approval',
                'setting_type': 'boolean',
                'value': 'true',
                'default_value': 'true',
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for setting_data in settings:
            setting, created = SystemSetting.objects.update_or_create(
                key=setting_data['key'],
                defaults=setting_data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created: {setting.display_name}'))
            else:
                updated_count += 1
                self.stdout.write(f'  Updated: {setting.display_name}')
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Seeded {created_count} new settings, updated {updated_count} existing'))
