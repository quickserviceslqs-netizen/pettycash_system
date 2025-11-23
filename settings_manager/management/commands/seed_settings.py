from django.core.management.base import BaseCommand
from settings_manager.models import SystemSetting


class Command(BaseCommand):
    help = 'Seed default system settings'

    def handle(self, *args, **options):
        settings = [
            # EMAIL SETTINGS
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
                'key': 'EMAIL_REPLY_TO',
                'display_name': 'Email Reply-To Address',
                'description': 'Reply-to email address for system notifications',
                'category': 'email',
                'setting_type': 'email',
                'value': 'support@pettycash.local',
                'default_value': 'support@pettycash.local',
            },
            {
                'key': 'EMAIL_SUBJECT_PREFIX',
                'display_name': 'Email Subject Prefix',
                'description': 'Prefix added to all email subjects',
                'category': 'email',
                'setting_type': 'string',
                'value': '[Petty Cash System]',
                'default_value': '[Petty Cash System]',
            },
            
            # APPROVAL SETTINGS
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
                'key': 'MAX_REQUISITION_AMOUNT',
                'display_name': 'Maximum Requisition Amount',
                'description': 'Maximum amount allowed for a single requisition',
                'category': 'approval',
                'setting_type': 'integer',
                'value': '1000000',
                'default_value': '1000000',
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
            {
                'key': 'ALLOW_SELF_APPROVAL',
                'display_name': 'Allow Self-Approval',
                'description': 'Allow users to approve their own requisitions (Not recommended)',
                'category': 'approval',
                'setting_type': 'boolean',
                'value': 'false',
                'default_value': 'false',
            },
            
            # PAYMENT SETTINGS
            {
                'key': 'PAYMENT_APPROVAL_REQUIRED',
                'display_name': 'Payment Approval Required',
                'description': 'Require treasury approval before executing payments',
                'category': 'payment',
                'setting_type': 'boolean',
                'value': 'true',
                'default_value': 'true',
            },
            {
                'key': 'MAX_PAYMENT_AMOUNT_WITHOUT_CFO',
                'display_name': 'Max Payment Amount Without CFO',
                'description': 'Maximum payment amount that can be processed without CFO approval',
                'category': 'payment',
                'setting_type': 'integer',
                'value': '500000',
                'default_value': '500000',
            },
            {
                'key': 'PAYMENT_RECEIPT_REQUIRED',
                'display_name': 'Payment Receipt Required',
                'description': 'Require receipt upload before payment execution',
                'category': 'payment',
                'setting_type': 'boolean',
                'value': 'true',
                'default_value': 'true',
            },
            {
                'key': 'PAYMENT_BATCH_PROCESSING',
                'display_name': 'Enable Batch Payment Processing',
                'description': 'Allow multiple payments to be processed at once',
                'category': 'payment',
                'setting_type': 'boolean',
                'value': 'true',
                'default_value': 'true',
            },
            
            # SECURITY SETTINGS
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
                'key': 'SESSION_TIMEOUT_MINUTES',
                'display_name': 'Session Timeout (Minutes)',
                'description': 'User session timeout in minutes (0 for browser session)',
                'category': 'security',
                'setting_type': 'integer',
                'value': '60',
                'default_value': '60',
            },
            {
                'key': 'PASSWORD_RESET_TIMEOUT_DAYS',
                'display_name': 'Password Reset Link Validity (Days)',
                'description': 'Number of days password reset links remain valid',
                'category': 'security',
                'setting_type': 'integer',
                'value': '1',
                'default_value': '1',
            },
            {
                'key': 'MAX_LOGIN_ATTEMPTS',
                'display_name': 'Maximum Login Attempts',
                'description': 'Maximum failed login attempts before account lockout',
                'category': 'security',
                'setting_type': 'integer',
                'value': '5',
                'default_value': '5',
            },
            
            # NOTIFICATION SETTINGS
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
                'key': 'PAYMENT_EMAIL_NOTIFICATIONS',
                'display_name': 'Send Payment Confirmation Emails',
                'description': 'Send email notifications when payments are executed',
                'category': 'notifications',
                'setting_type': 'boolean',
                'value': 'true',
                'default_value': 'true',
            },
            {
                'key': 'REJECTION_EMAIL_NOTIFICATIONS',
                'display_name': 'Send Rejection Notifications',
                'description': 'Email users when their requisitions are rejected',
                'category': 'notifications',
                'setting_type': 'boolean',
                'value': 'true',
                'default_value': 'true',
            },
            {
                'key': 'DAILY_SUMMARY_EMAILS',
                'display_name': 'Send Daily Summary Emails',
                'description': 'Send daily summary of pending actions to approvers',
                'category': 'notifications',
                'setting_type': 'boolean',
                'value': 'false',
                'default_value': 'false',
            },
            
            # GENERAL SETTINGS
            {
                'key': 'SYSTEM_MAINTENANCE_MODE',
                'display_name': 'Maintenance Mode',
                'description': 'Enable maintenance mode (blocks non-admin access)',
                'category': 'general',
                'setting_type': 'boolean',
                'value': 'false',
                'default_value': 'false',
            },
            {
                'key': 'CURRENCY_CODE',
                'display_name': 'Default Currency Code',
                'description': 'Default currency for all transactions (ISO 4217 code)',
                'category': 'general',
                'setting_type': 'string',
                'value': 'KES',
                'default_value': 'KES',
            },
            {
                'key': 'DATE_FORMAT',
                'display_name': 'Date Display Format',
                'description': 'Date format for display throughout the system',
                'category': 'general',
                'setting_type': 'string',
                'value': 'Y-m-d',
                'default_value': 'Y-m-d',
            },
            {
                'key': 'PAGINATION_PAGE_SIZE',
                'display_name': 'Items Per Page',
                'description': 'Number of items to display per page in lists',
                'category': 'general',
                'setting_type': 'integer',
                'value': '25',
                'default_value': '25',
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
        
        # Summary by category
        category_counts = {}
        for setting in SystemSetting.objects.filter(is_active=True):
            category_counts[setting.category] = category_counts.get(setting.category, 0) + 1
        
        self.stdout.write('\nSettings by category:')
        for category, count in sorted(category_counts.items()):
            self.stdout.write(f'  {category.title()}: {count}')
