"""
Additional notification, workflow, and security alert settings for full coverage
Standalone Django script: run with `python scripts/seed_additional_notification_settings.py`
"""
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
django.setup()
from settings_manager.models import SystemSetting

def seed_additional_notification_settings():
    settings = [
        # Workflow & SLA Notifications
        {
            'key': 'APPROVAL_ESCALATION_EMAIL_NOTIFICATIONS',
            'display_name': 'Send Email on Approval Escalation',
            'description': 'Enable/disable email when approval is auto-escalated.',
            'category': 'notifications',
            'setting_type': 'boolean',
            'value': 'true',
            'default_value': 'true',
        },
        {
            'key': 'APPROVAL_ESCALATION_ALERT_RECIPIENTS',
            'display_name': 'Approval Escalation Alert Recipients',
            'description': 'Comma-separated emails for escalation alerts.',
            'category': 'notifications',
            'setting_type': 'string',
            'value': '',
            'default_value': '',
        },
        {
            'key': 'SLA_BREACH_EMAIL_NOTIFICATIONS',
            'display_name': 'Send Email on SLA Breach',
            'description': 'Enable/disable email when SLA is breached.',
            'category': 'notifications',
            'setting_type': 'boolean',
            'value': 'true',
            'default_value': 'true',
        },
        {
            'key': 'SLA_BREACH_ALERT_RECIPIENTS',
            'display_name': 'SLA Breach Alert Recipients',
            'description': 'Comma-separated emails for SLA breach alerts.',
            'category': 'notifications',
            'setting_type': 'string',
            'value': '',
            'default_value': '',
        },
        # Overdue & Critical Alerts
        {
            'key': 'SEND_CRITICAL_OVERDUE_ALERTS',
            'display_name': 'Send Critical Overdue Alerts',
            'description': 'Enable/disable critical overdue alerts.',
            'category': 'notifications',
            'setting_type': 'boolean',
            'value': 'true',
            'default_value': 'true',
        },
        {
            'key': 'CRITICAL_OVERDUE_ALERT_RECIPIENTS',
            'display_name': 'Critical Overdue Alert Recipients',
            'description': 'Comma-separated emails for critical overdue alerts.',
            'category': 'notifications',
            'setting_type': 'string',
            'value': '',
            'default_value': '',
        },
        # Security & Incident Notifications
        {
            'key': 'SECURITY_ALERT_EMAIL_NOTIFICATIONS',
            'display_name': 'Send Security Incident Emails',
            'description': 'Enable/disable security incident emails.',
            'category': 'security',
            'setting_type': 'boolean',
            'value': 'true',
            'default_value': 'true',
        },
        {
            'key': 'FRAUD_ALERT_EMAIL_NOTIFICATIONS',
            'display_name': 'Send Fraud Detection Emails',
            'description': 'Enable/disable fraud detection emails.',
            'category': 'security',
            'setting_type': 'boolean',
            'value': 'true',
            'default_value': 'true',
        },
        {
            'key': 'FRAUD_ALERT_RECIPIENTS',
            'display_name': 'Fraud Alert Recipients',
            'description': 'Comma-separated emails for fraud alerts.',
            'category': 'security',
            'setting_type': 'string',
            'value': '',
            'default_value': '',
        },
        # System & Maintenance Notifications
        {
            'key': 'SYSTEM_MAINTENANCE_EMAIL_NOTIFICATIONS',
            'display_name': 'Send System Maintenance Emails',
            'description': 'Enable/disable system maintenance emails.',
            'category': 'notifications',
            'setting_type': 'boolean',
            'value': 'true',
            'default_value': 'true',
        },
        {
            'key': 'SYSTEM_MAINTENANCE_ALERT_RECIPIENTS',
            'display_name': 'System Maintenance Alert Recipients',
            'description': 'Comma-separated emails for maintenance alerts.',
            'category': 'notifications',
            'setting_type': 'string',
            'value': '',
            'default_value': '',
        },
        # Optional Channels
        {
            'key': 'SMS_NOTIFICATIONS_ENABLED',
            'display_name': 'Enable SMS Notifications',
            'description': 'Enable/disable SMS notifications.',
            'category': 'notifications',
            'setting_type': 'boolean',
            'value': 'false',
            'default_value': 'false',
        },
        {
            'key': 'WEBHOOK_NOTIFICATIONS_ENABLED',
            'display_name': 'Enable Webhook Notifications',
            'description': 'Enable/disable webhook notifications.',
            'category': 'notifications',
            'setting_type': 'boolean',
            'value': 'false',
            'default_value': 'false',
        },
        {
            'key': 'SLACK_NOTIFICATIONS_ENABLED',
            'display_name': 'Enable Slack/Teams Notifications',
            'description': 'Enable/disable Slack/Teams notifications.',
            'category': 'notifications',
            'setting_type': 'boolean',
            'value': 'false',
            'default_value': 'false',
        },
    ]
    for s in settings:
        obj, created = SystemSetting.objects.get_or_create(key=s['key'], defaults=s)
        if not created:
            for k, v in s.items():
                setattr(obj, k, v)
            obj.save()

if __name__ == "__main__":
    seed_additional_notification_settings()
