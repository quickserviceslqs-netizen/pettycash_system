from django.contrib.auth import get_user_model
from django.db.models import Q
from workflow.models import ApprovalThreshold
from workflow.services.resolver_helpers import (
    build_base_roles, find_candidate_for_role, resolve_candidate_list,
    apply_auto_escalation, assign_slas
)
from django.core.exceptions import PermissionDenied
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

# Centralized roles that are not filtered by branch/region/company
CENTRALIZED_ROLES = ["treasury", "fp&a", "group_finance_manager", "cfo", "ceo", "admin"]


def can_approve(requisition, user):
    """Compatibility wrapper: return whether `user` can approve `requisition`.

    Many older call sites import `can_approve` from this module; forward
    to the model's `can_approve` method when available. Fall back to a
    conservative check using `next_approver`.
    """
    try:
        return requisition.can_approve(user)
    except AttributeError:
        # Fallback: only allow if next_approver matches the user
        if getattr(requisition, 'next_approver', None) is None:
            return False
        try:
            return requisition.next_approver.id == user.id
        except Exception:
            return False


def get_approval_deadline_hours():
    """Get approval deadline hours from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('APPROVAL_SLA_HOURS', '48'))


def allow_self_approval():
    """Check if self-approval is allowed from settings."""
    from settings_manager.models import get_setting
    return get_setting('AUTO_APPROVE_BELOW_THRESHOLD', 'false') == 'true'


def get_auto_escalate_days():
    """Get auto-escalate days from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('AUTO_ESCALATE_AFTER_DAYS', '3'))


def is_business_hours_only():
    """Check if workflow processing is business hours only."""
    from settings_manager.models import get_setting
    return get_setting('BUSINESS_HOURS_ONLY', 'false') == 'true'


def is_parallel_approvals_enabled():
    """Check if parallel approvals are enabled."""
    from settings_manager.models import get_setting
    return get_setting('PARALLEL_APPROVALS_ENABLED', 'false') == 'true'


def is_weekend_processing_enabled():
    """Check if weekend processing is enabled."""
    from settings_manager.models import get_setting
    return get_setting('WEEKEND_PROCESSING_ENABLED', 'false') == 'true'


def get_overdue_threshold_hours():
    """Get overdue threshold hours from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('OVERDUE_THRESHOLD_HOURS', '72'))


def get_critical_overdue_hours():
    """Get critical overdue threshold hours from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('CRITICAL_OVERDUE_HOURS', '120'))


def get_end_to_end_sla_days():
    """Get end-to-end SLA days from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('END_TO_END_SLA_DAYS', '5'))


def get_payment_sla_hours():
    """Get payment SLA hours from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('PAYMENT_SLA_HOURS', '24'))


def get_validation_sla_hours():
    """Get treasury validation SLA hours from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('VALIDATION_SLA_HOURS', '24'))


def is_delegate_approvals_enabled():
    """Check if approval delegation is enabled."""
    from settings_manager.models import get_setting
    return get_setting('DELEGATE_APPROVALS_ENABLED', 'true') == 'true'


def get_approval_reminder_frequency():
    """Get approval reminder frequency hours from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('APPROVAL_REMINDER_FREQUENCY_HOURS', '24'))


def is_track_workflow_metrics():
    """Check if workflow metrics tracking is enabled."""
    from settings_manager.models import get_setting
    return get_setting('TRACK_WORKFLOW_METRICS', 'true') == 'true'


# Approval Settings Helper Functions

def allow_self_approval_approval():
    """Check if self-approval is allowed from approval settings."""
    from settings_manager.models import get_setting
    return get_setting('ALLOW_SELF_APPROVAL', 'false') == 'true'


def is_auto_reject_expired_changes():
    """Check if auto-reject expired change requests is enabled."""
    from settings_manager.models import get_setting
    return get_setting('AUTO_REJECT_EXPIRED_CHANGES', 'true') == 'true'


def get_auto_reject_pending_hours():
    """Get auto-reject pending after hours from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('AUTO_REJECT_PENDING_AFTER_HOURS', '72'))


def get_default_approval_deadline_hours():
    """Get default approval deadline hours from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('DEFAULT_APPROVAL_DEADLINE_HOURS', '24'))


def get_default_change_request_deadline_hours():
    """Get default change request deadline hours from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('DEFAULT_CHANGE_REQUEST_DEADLINE_HOURS', '48'))


def is_approval_escalation_enabled():
    """Check if approval escalation is enabled."""
    from settings_manager.models import get_setting
    return get_setting('APPROVAL_ESCALATION_ENABLED', 'true') == 'true'


def is_approval_notification_enabled():
    """Check if approval notifications are enabled."""
    from settings_manager.models import get_setting
    return get_setting('APPROVAL_NOTIFICATION_ENABLED', 'true') == 'true'


def is_fast_track_enabled():
    """Check if fast-track approvals are enabled."""
    from settings_manager.models import get_setting
    return get_setting('FAST_TRACK_ENABLED', 'true') == 'true'


def get_max_approvals_per_requisition():
    """Get maximum approvals per requisition from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('MAX_APPROVALS_PER_REQUISITION', '5'))


def get_max_requisition_amount():
    """Get maximum requisition amount from settings."""
    from settings_manager.models import get_setting
    return float(get_setting('MAX_REQUISITION_AMOUNT', '1000000'))


# Email Settings Helper Functions

def get_system_email_from():
    """Get system email from address from settings."""
    from settings_manager.models import get_setting
    return get_setting('SYSTEM_EMAIL_FROM', 'noreply@pettycash.local')


def get_email_reply_to():
    """Get email reply-to address from settings."""
    from settings_manager.models import get_setting
    return get_setting('EMAIL_REPLY_TO', 'support@pettycash.local')


def get_email_subject_prefix():
    """Get email subject prefix from settings."""
    from settings_manager.models import get_setting
    return get_setting('EMAIL_SUBJECT_PREFIX', '[Petty Cash System]')


# Payment Settings Helper Functions

def is_payment_batch_processing_enabled():
    """Check if batch payment processing is enabled."""
    from settings_manager.models import get_setting
    return get_setting('PAYMENT_BATCH_PROCESSING', 'true') == 'true'


def get_max_payment_without_ceo():
    """Get maximum payment amount without CEO approval."""
    from settings_manager.models import get_setting
    return float(get_setting('MAX_PAYMENT_AMOUNT_WITHOUT_CEO', '1000000'))


def get_max_payment_without_cfo():
    """Get maximum payment amount without CFO approval."""
    from settings_manager.models import get_setting
    return float(get_setting('MAX_PAYMENT_AMOUNT_WITHOUT_CFO', '500000'))


def is_payment_multi_approval_enabled():
    """Check if multi-level payment approval is enabled."""
    from settings_manager.models import get_setting
    return get_setting('PAYMENT_MULTI_APPROVAL_ENABLED', 'false') == 'true'


def is_payment_approval_required():
    """Check if payment approval is required."""
    from settings_manager.models import get_setting
    return get_setting('PAYMENT_APPROVAL_REQUIRED', 'true') == 'true'


def is_payment_hold_enabled():
    """Check if payment hold is enabled."""
    from settings_manager.models import get_setting
    return get_setting('PAYMENT_HOLD_ENABLED', 'false') == 'true'


def get_payment_method_restrictions():
    """Get payment method restrictions from settings."""
    from settings_manager.models import get_setting
    import json
    restrictions_str = get_setting('PAYMENT_METHOD_RESTRICTIONS', '{"mpesa": {"max": 100000}, "bank": {"min": 10000}}')
    try:
        return json.loads(restrictions_str)
    except (json.JSONDecodeError, TypeError):
        return {"mpesa": {"max": 100000}, "bank": {"min": 10000}}


def get_payment_notification_recipients():
    """Get payment notification recipients from settings."""
    from settings_manager.models import get_setting
    recipients = get_setting('PAYMENT_NOTIFICATION_RECIPIENTS', '')
    return [r.strip() for r in recipients.split(',') if r.strip()]


def is_payment_receipt_required():
    """Check if payment receipt is required."""
    from settings_manager.models import get_setting
    return get_setting('PAYMENT_RECEIPT_REQUIRED', 'true') == 'true'


def get_payment_time_window():
    """Get payment time window from settings."""
    from settings_manager.models import get_setting
    return get_setting('PAYMENT_TIME_WINDOW', '08:00-18:00')


# Security Settings Helper Functions

def get_require_2fa_above_amount():
    """Get 2FA requirement threshold from settings."""
    from settings_manager.models import get_setting
    return float(get_setting('REQUIRE_2FA_ABOVE_AMOUNT', '100000'))


def get_account_lockout_duration():
    """Get account lockout duration in minutes from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('ACCOUNT_LOCKOUT_DURATION_MINUTES', '30'))


def get_activity_log_retention_days():
    """Get activity log retention period from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('ACTIVITY_LOG_RETENTION_DAYS', '365'))


def is_alert_multiple_sessions():
    """Check if multiple session alerts are enabled."""
    from settings_manager.models import get_setting
    return get_setting('ALERT_MULTIPLE_CONCURRENT_SESSIONS', 'true') == 'true'


def is_alert_unusual_time():
    """Check if off-hours access alerts are enabled."""
    from settings_manager.models import get_setting
    return get_setting('ALERT_UNUSUAL_TIME', 'true') == 'true'


def is_alert_rapid_transactions():
    """Check if rapid transaction alerts are enabled."""
    from settings_manager.models import get_setting
    return get_setting('ALERT_RAPID_TRANSACTIONS', 'true') == 'true'


def is_alert_unusual_location():
    """Check if unusual location alerts are enabled."""
    from settings_manager.models import get_setting
    return get_setting('ALERT_UNUSUAL_LOCATION', 'true') == 'true'


def get_allowed_ip_addresses():
    """Get allowed IP addresses from settings."""
    from settings_manager.models import get_setting
    ips = get_setting('ALLOWED_IP_ADDRESSES', '')
    return [ip.strip() for ip in ips.split(',') if ip.strip()]


def is_auto_logout_on_browser_close():
    """Check if auto logout on browser close is enabled."""
    from settings_manager.models import get_setting
    return get_setting('AUTO_LOGOUT_ON_BROWSER_CLOSE', 'true') == 'true'


def get_business_hours_start():
    """Get business hours start time from settings."""
    from settings_manager.models import get_setting
    return get_setting('BUSINESS_HOURS_START', '08:00')


def get_business_hours_end():
    """Get business hours end time from settings."""
    from settings_manager.models import get_setting
    return get_setting('BUSINESS_HOURS_END', '18:00')


def calculate_business_hours(start_time, end_time, business_hours_only, weekend_processing):
    """Calculate elapsed hours considering business hours and weekend processing."""
    from django.utils import timezone
    import datetime

    if not business_hours_only:
        # Simple total hours
        delta = end_time - start_time
        return delta.total_seconds() / 3600

    # Business hours calculation (simplified)
    total_hours = 0
    current = start_time

    while current < end_time:
        if current.weekday() < 5 or weekend_processing:  # Monday to Friday or weekend processing enabled
            start_hour = int(get_business_hours_start().split(':')[0])
            end_hour = int(get_business_hours_end().split(':')[0])
            if start_hour <= current.hour < end_hour:
                # Within business hours
                next_hour = current.replace(hour=min(current.hour + 1, end_hour), minute=0, second=0, microsecond=0)
                if next_hour > end_time:
                    next_hour = end_time
                total_hours += (next_hour - current).total_seconds() / 3600
                current = next_hour
            else:
                # Outside business hours, skip to next business hour
                if current.hour < start_hour:
                    current = current.replace(hour=start_hour, minute=0, second=0, microsecond=0)
                else:
                    # Next day
                    current = (current + datetime.timedelta(days=1)).replace(hour=start_hour, minute=0, second=0, microsecond=0)
        else:
            # Weekend, skip to Monday
            days_to_monday = (7 - current.weekday()) % 7
            if days_to_monday == 0:
                days_to_monday = 7
            current = (current + datetime.timedelta(days=days_to_monday)).replace(hour=int(get_business_hours_start().split(':')[0]), minute=0, second=0, microsecond=0)

    return total_hours


def is_activity_geolocation_enabled():
    """Check if activity geolocation tracking is enabled."""
    from settings_manager.models import get_setting
    return get_setting('ENABLE_ACTIVITY_GEOLOCATION', 'true') == 'true'


def is_data_masking_enabled():
    """Check if data masking is enabled."""
    from settings_manager.models import get_setting
    return get_setting('ENABLE_DATA_MASKING', 'true') == 'true'


def is_transaction_signing_enabled():
    """Check if digital transaction signing is enabled."""
    from settings_manager.models import get_setting
    return get_setting('ENABLE_TRANSACTION_SIGNING', 'false') == 'true'


def is_fraud_detection_enabled():
    """Check if fraud detection is enabled."""
    from settings_manager.models import get_setting
    return get_setting('ENABLE_FRAUD_DETECTION', 'true') == 'true'


def is_ip_whitelist_enabled():
    """Check if IP whitelist is enabled."""
    from settings_manager.models import get_setting
    return get_setting('ENABLE_IP_WHITELIST', 'false') == 'true'


def is_two_factor_auth_enabled():
    """Check if two-factor authentication is enabled globally."""
    from settings_manager.models import get_setting
    return get_setting('ENABLE_TWO_FACTOR_AUTH', 'false') == 'true'


def is_audit_trail_encryption_enabled():
    """Check if audit trail encryption is enabled."""
    from settings_manager.models import get_setting
    return get_setting('ENABLE_AUDIT_TRAIL_ENCRYPTION', 'false') == 'true'


def is_device_whitelist_enforced():
    """Check if device whitelisting is enforced."""
    from settings_manager.models import get_setting
    return get_setting('ENFORCE_DEVICE_WHITELIST', 'false') == 'true'


def get_password_change_days():
    """Get password change requirement in days from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('REQUIRE_PASSWORD_CHANGE_DAYS', '90'))


def get_fraud_alert_recipients():
    """Get fraud alert recipients from settings."""
    from settings_manager.models import get_setting
    recipients = get_setting('FRAUD_ALERT_RECIPIENTS', '')
    return [r.strip() for r in recipients.split(',') if r.strip()]


def is_2fa_required_for_approvers():
    """Check if 2FA is required for approvers."""
    from settings_manager.models import get_setting
    return get_setting('REQUIRE_2FA_FOR_APPROVERS', 'false') == 'true'


def get_max_login_attempts():
    """Get maximum login attempts from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('MAX_LOGIN_ATTEMPTS', '5'))


def get_min_password_length():
    """Get minimum password length from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('MIN_PASSWORD_LENGTH', '12'))


def get_password_reset_timeout_days():
    """Get password reset timeout in days from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('PASSWORD_RESET_TIMEOUT_DAYS', '1'))


def get_prevent_password_reuse():
    """Get password reuse prevention count from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('PREVENT_PASSWORD_REUSE', '5'))


def get_rapid_transaction_threshold():
    """Get rapid transaction threshold from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('RAPID_TRANSACTION_THRESHOLD', '5'))


def get_rapid_transaction_window():
    """Get rapid transaction window in minutes from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('RAPID_TRANSACTION_WINDOW_MINUTES', '10'))


def is_password_complexity_required():
    """Check if password complexity is required."""
    from settings_manager.models import get_setting
    return get_setting('REQUIRE_PASSWORD_COMPLEXITY', 'true') == 'true'


def get_security_alert_recipients():
    """Get security alert recipients from settings."""
    from settings_manager.models import get_setting
    recipients = get_setting('SECURITY_ALERT_RECIPIENTS', 'security@company.com,admin@company.com')
    return [r.strip() for r in recipients.split(',') if r.strip()]


def is_fraud_alert_emails_enabled():
    """Check if fraud alert emails are enabled."""
    from settings_manager.models import get_setting
    return get_setting('FRAUD_ALERT_EMAIL_NOTIFICATIONS', 'true') == 'true'


def is_security_alert_emails_enabled():
    """Check if security alert emails are enabled."""
    from settings_manager.models import get_setting
    return get_setting('SECURITY_ALERT_EMAIL_NOTIFICATIONS', 'true') == 'true'


def get_session_timeout_minutes():
    """Get session timeout in minutes from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('SESSION_TIMEOUT_MINUTES', '30'))


def get_transaction_signing_threshold():
    """Get transaction signing threshold from settings."""
    from settings_manager.models import get_setting
    return float(get_setting('TRANSACTION_SIGNING_THRESHOLD', '500000'))


def get_invitation_expiry_days():
    """Get user invitation expiry in days from settings."""
    from settings_manager.models import get_setting
    return int(get_setting('INVITATION_EXPIRY_DAYS', '7'))


# Advanced Security Settings Helper Functions

def is_force_https_enabled():
    """Check if HTTPS is forced."""
    from settings_manager.models import get_setting
    return get_setting('FORCE_HTTPS', True)


def is_login_notification_enabled():
    """Check if login notifications are enabled."""
    from settings_manager.models import get_setting
    return get_setting('LOGIN_NOTIFICATION_ENABLED', True)


def get_password_expiry_days():
    """Get password expiry period in days."""
    from settings_manager.models import get_setting
    return int(get_setting('PASSWORD_EXPIRY_DAYS', '90'))


def get_rate_limit_login_attempts():
    """Get rate limit for login attempts."""
    from settings_manager.models import get_setting
    return int(get_setting('RATE_LIMIT_LOGIN_ATTEMPTS', '20'))


# Notification Settings Helper Functions

def is_slack_notifications_enabled():
    """Check if Slack/Teams notifications are enabled."""
    from settings_manager.models import get_setting
    return get_setting('SLACK_NOTIFICATIONS_ENABLED', 'false') == 'true'


def is_sms_notifications_enabled():
    """Check if SMS notifications are enabled."""
    from settings_manager.models import get_setting
    return get_setting('SMS_NOTIFICATIONS_ENABLED', 'false') == 'true'


def is_webhook_notifications_enabled():
    """Check if webhook notifications are enabled."""
    from settings_manager.models import get_setting
    return get_setting('WEBHOOK_NOTIFICATIONS_ENABLED', 'false') == 'true'


def is_send_critical_overdue_alerts():
    """Check if critical overdue alerts should be sent."""
    from settings_manager.models import get_setting
    return get_setting('SEND_CRITICAL_OVERDUE_ALERTS', 'true') == 'true'


def is_daily_summary_emails_enabled():
    """Check if daily summary emails are enabled."""
    from settings_manager.models import get_setting
    return get_setting('DAILY_SUMMARY_EMAILS', 'false') == 'true'


def is_approval_email_notifications_enabled():
    """Check if approval email notifications are enabled."""
    from settings_manager.models import get_setting
    return get_setting('APPROVAL_EMAIL_NOTIFICATIONS', 'true') == 'true'


def is_approval_escalation_email_notifications_enabled():
    """Check if approval escalation email notifications are enabled."""
    from settings_manager.models import get_setting
    return get_setting('APPROVAL_ESCALATION_EMAIL_NOTIFICATIONS', 'true') == 'true'


def is_sla_breach_email_notifications_enabled():
    """Check if SLA breach email notifications are enabled."""
    from settings_manager.models import get_setting
    return get_setting('SLA_BREACH_EMAIL_NOTIFICATIONS', 'true') == 'true'


def is_payment_email_notifications_enabled():
    """Check if payment email notifications are enabled."""
    from settings_manager.models import get_setting
    return get_setting('PAYMENT_EMAIL_NOTIFICATIONS', 'true') == 'true'


def is_rejection_email_notifications_enabled():
    """Check if rejection email notifications are enabled."""
    from settings_manager.models import get_setting
    return get_setting('REJECTION_EMAIL_NOTIFICATIONS', 'true') == 'true'


def is_system_maintenance_email_notifications_enabled():
    """Check if system maintenance email notifications are enabled."""
    from settings_manager.models import get_setting
    return get_setting('SYSTEM_MAINTENANCE_EMAIL_NOTIFICATIONS', 'true') == 'true'


def get_approval_escalation_alert_recipients():
    """Get approval escalation alert recipients from settings."""
    from settings_manager.models import get_setting
    recipients = get_setting('APPROVAL_ESCALATION_ALERT_RECIPIENTS', '')
    return [r.strip() for r in recipients.split(',') if r.strip()]


def get_critical_overdue_alert_recipients():
    """Get critical overdue alert recipients from settings."""
    from settings_manager.models import get_setting
    recipients = get_setting('CRITICAL_OVERDUE_ALERT_RECIPIENTS', '')
    return [r.strip() for r in recipients.split(',') if r.strip()]


def get_sla_breach_alert_recipients():
    """Get SLA breach alert recipients from settings."""
    from settings_manager.models import get_setting
    recipients = get_setting('SLA_BREACH_ALERT_RECIPIENTS', '')
    return [r.strip() for r in recipients.split(',') if r.strip()]


def get_system_maintenance_alert_recipients():
    """Get system maintenance alert recipients from settings."""
    from settings_manager.models import get_setting
    recipients = get_setting('SYSTEM_MAINTENANCE_ALERT_RECIPIENTS', '')
    return [r.strip() for r in recipients.split(',') if r.strip()]


# Reporting Settings Helper Functions

def is_auto_generate_monthly_reports_enabled():
    """Check if auto-generation of monthly reports is enabled."""
    from settings_manager.models import get_setting
    return get_setting('AUTO_GENERATE_MONTHLY_REPORTS', 'false') == 'true'


def get_report_privacy_level():
    """Get the default report privacy level."""
    from settings_manager.models import get_setting
    return get_setting('REPORT_PRIVACY_LEVEL', 'restricted')


def is_report_audit_trail_enabled():
    """Check if report audit trail is enabled."""
    from settings_manager.models import get_setting
    return get_setting('ENABLE_REPORT_AUDIT_TRAIL', 'true') == 'true'


def is_report_data_masking_enabled():
    """Check if report data masking is enabled."""
    from settings_manager.models import get_setting
    return get_setting('REPORT_DATA_MASKING', 'true') == 'true'


def is_report_scheduling_enabled():
    """Check if report scheduling is enabled."""
    from settings_manager.models import get_setting
    return get_setting('REPORT_SCHEDULING_ENABLED', 'false') == 'true'


def get_financial_year_start_month():
    """Get the financial year start month."""
    from settings_manager.models import get_setting
    return int(get_setting('FINANCIAL_YEAR_START_MONTH', '1'))


def get_report_access_roles():
    """Get the roles allowed to access reports."""
    from settings_manager.models import get_setting
    roles = get_setting('REPORT_ACCESS_ROLES', 'admin,finance,manager')
    return [r.strip() for r in roles.split(',') if r.strip()]


def get_report_email_recipients():
    """Get the email recipients for reports."""
    from settings_manager.models import get_setting
    recipients = get_setting('REPORT_EMAIL_RECIPIENTS', 'finance@company.local')
    return [r.strip() for r in recipients.split(',') if r.strip()]


def get_report_export_formats():
    """Get the allowed report export formats."""
    from settings_manager.models import get_setting
    formats = get_setting('REPORT_EXPORT_FORMATS', 'pdf,excel,csv')
    return [f.strip() for f in formats.split(',') if f.strip()]


def get_report_kpi_list():
    """Get the list of KPIs to include in reports."""
    from settings_manager.models import get_setting
    kpis = get_setting('REPORT_KPI_LIST', 'total_amount,avg_amount,approval_rate,payment_success_rate')
    return [k.strip() for k in kpis.split(',') if k.strip()]


def get_report_retention_months():
    """Get the report retention period in months."""
    from settings_manager.models import get_setting
    return int(get_setting('REPORT_RETENTION_MONTHS', '24'))


def get_report_template_choices():
    """Get the available report template choices."""
    from settings_manager.models import get_setting
    templates = get_setting('REPORT_TEMPLATE_CHOICES', 'default,summary,detailed')
    return [t.strip() for t in templates.split(',') if t.strip()]


def get_report_timezone():
    """Get the report timezone."""
    from settings_manager.models import get_setting
    return get_setting('REPORT_TIMEZONE', 'Africa/Nairobi')
    """
    Calculate hours between two timestamps considering business hours and weekend settings.
    """
    if not business_hours_only:
        return (end_time - start_time).total_seconds() / 3600

    # Business hours: 9 AM to 5 PM, Monday to Friday
    total_hours = 0
    current = start_time

    while current < end_time:
        # Skip weekends if weekend processing is disabled
        if not weekend_processing and current.weekday() >= 5:  # Saturday = 5, Sunday = 6
            current += timezone.timedelta(days=1)
            current = current.replace(hour=9, minute=0, second=0, microsecond=0)
            continue

        # If weekday and within business hours
        if current.weekday() < 5:  # Monday to Friday
            business_start = current.replace(hour=9, minute=0, second=0, microsecond=0)
            business_end = current.replace(hour=17, minute=0, second=0, microsecond=0)

            # Adjust for current time
            effective_start = max(current, business_start)
            effective_end = min(end_time, business_end)

            if effective_start < effective_end:
                total_hours += (effective_end - effective_start).total_seconds() / 3600

        # Move to next day
        current += timezone.timedelta(days=1)
        current = current.replace(hour=9, minute=0, second=0, microsecond=0)

    return total_hours



def find_approval_threshold(amount, origin_type):
    """
    Find a matching ApprovalThreshold for the requisition.
    """
    thresholds = (
        ApprovalThreshold.objects.filter(is_active=True)
        .filter(Q(origin_type=origin_type.upper()) | Q(origin_type='ANY'))
        .order_by('priority', 'min_amount')
    )

    for thr in thresholds:
        if thr.min_amount <= amount <= thr.max_amount:
            return thr
    return None


def resolve_workflow(requisition):
    """
    Build approval workflow based on threshold, origin, urgency, and requester role.
    Handles:
    - Case-insensitive role matching
    - Centralized roles
    - Scoped routing
    - No-self-approval
    - Treasury-originated overrides
    - Urgent fast-track
    """
    if not requisition.applied_threshold:
        thr = find_approval_threshold(requisition.amount, requisition.origin_type)
        if not thr:
            raise ValueError("No ApprovalThreshold found for this requisition.")

        requisition.applied_threshold = thr
        requisition.tier = thr.name
        requisition.save(update_fields=["applied_threshold", "tier"])

    # 0️⃣ Maximum amount validation (from approval settings)
    max_amount = get_max_requisition_amount()
    if requisition.amount > max_amount:
        raise ValueError(f"Requisition amount {requisition.amount} exceeds maximum allowed amount of {max_amount}")

    base_roles = requisition.applied_threshold.roles_sequence  # e.g., ["BRANCH_MANAGER","TREASURY"]
    # Ensure Treasury is not part of the approval chain — Treasury is a validator, not an approver
    try:
        base_roles = [r for r in base_roles if str(r).lower() != 'treasury']
    except Exception:
        base_roles = [r for r in base_roles]
    resolved = []

    # 2️⃣ Treasury special case override
    is_treasury_request = requisition.requested_by.role.lower() == "treasury"
    if is_treasury_request:
        tier = requisition.tier
        if tier in ["Tier 1", "Tier1"]:
            base_roles = ["department_head", "group_finance_manager"]
        elif tier in ["Tier 2", "Tier2", "Tier 3", "Tier3"]:
            base_roles = ["group_finance_manager", "cfo"]

    # Maximum amount validation (from approval settings)
    max_amount = get_max_requisition_amount()
    if requisition.amount > max_amount:
        raise ValueError(f"Requisition amount {requisition.amount} exceeds maximum allowed amount of {max_amount}")

    # Build base roles (excludes treasury and applies treasury-origin overrides)
    base_roles = build_base_roles(requisition, allow_self_approval=allow_self_approval_approval())

    # Auto-escalation and processing settings
    auto_escalate_days = get_auto_escalate_days()
    business_hours_only = is_business_hours_only()
    weekend_processing = is_weekend_processing_enabled()
    parallel_approvals = is_parallel_approvals_enabled()
    track_metrics = is_track_workflow_metrics()
    fast_track_enabled = is_fast_track_enabled()
    max_approvals = get_max_approvals_per_requisition()

    # Resolve candidate users for each role
    resolved = resolve_candidate_list(base_roles, requisition, parallel_approvals)

    # If no valid approvers found at all, escalate to admin
    if not resolved or all(r['user_id'] is None for r in resolved):
        admin = User.objects.filter(role__iexact='admin', is_active=True).first()
        if not admin:
            raise ValueError("No ADMIN user exists. Please create one with role='admin'.")
        escalation_reason = f"No approvers found in roles: {base_roles}"
        logger.warning(f"Auto-escalating {requisition.transaction_id} to admin: {escalation_reason}")
        resolved = [{
            'user_id': admin.id,
            'role': 'ADMIN',
            'auto_escalated': True,
            'escalation_reason': escalation_reason,
        }]

    # Fast-track urgent flow (same semantics as before)
    if (
        getattr(requisition, 'is_urgent', False)
        and fast_track_enabled
        and not requisition.tier.startswith('Tier 4')
        and len(resolved) > 1
        and resolved[-1].get('user_id') is not None
    ):
        logger.info(f"Phase 3 urgent fast-track for {requisition.transaction_id}: jumping to final approver")
        resolved = [resolved[-1]]

    # Apply auto-escalation to fill gaps
    resolved = apply_auto_escalation(resolved)

    # Truncate to max_approvals
    if len(resolved) > max_approvals:
        logger.warning(f"Truncating workflow for {requisition.transaction_id}: {len(resolved)} approvers exceeds maximum of {max_approvals}")
        resolved = resolved[:max_approvals]

    # Save workflow to requisition
    requisition.workflow_sequence = resolved
    requisition.next_approver = User.objects.get(id=resolved[0]['user_id'])
    requisition.save(update_fields=['workflow_sequence', 'next_approver'])

    # Send approval notification if enabled
    if is_approval_email_notifications_enabled():
        _send_approval_notification(requisition, resolved)

    # Assign SLA fields
    assign_slas(requisition, track_metrics=track_metrics, business_hours_only=business_hours_only, weekend_processing=weekend_processing)

    return resolved
    # Must be the next approver
    if not requisition.next_approver or user.id != requisition.next_approver.id:
        return False
    
    return True


def execute_payment(payment, executor_user):
    """
    Execute payment.
    Enforces:
    - Executor cannot be the original requester
    - Treasury self-request rules
    """
    if executor_user.id == payment.requisition.requested_by.id:
        raise PermissionDenied("Executor cannot be the original requester.")
    # Proceed with payment logic...


# Notification Helper Functions

def _send_approval_notification(requisition, workflow_sequence):
    """
    Send notification to the next approver that approval is needed.
    """
    if not workflow_sequence or not workflow_sequence[0].get('user_id'):
        return
    
    try:
        next_approver = User.objects.get(id=workflow_sequence[0]['user_id'])
        
        # Prepare notification content
        subject = f"Approval Required: {requisition.transaction_id}"
        message = f"""
Dear {next_approver.get_full_name()},

You have a new requisition requiring your approval:

Transaction ID: {requisition.transaction_id}
Requester: {requisition.requested_by.get_full_name()}
Amount: {requisition.amount}
Purpose: {requisition.purpose or 'Not specified'}

Please log in to the system to review and approve/reject this request.

Best regards,
Petty Cash System
"""
        
        # Send email notification
        from django.core.mail import send_mail
        from workflow.services.resolver import get_system_email_from
        
        send_mail(
            subject=subject,
            message=message,
            from_email=get_system_email_from(),
            recipient_list=[next_approver.email],
            fail_silently=True,  # Don't fail workflow if email fails
        )
        
        logger.info(f"Approval notification sent to {next_approver.email} for {requisition.transaction_id}")
        
    except Exception as e:
        logger.error(f"Failed to send approval notification: {e}")


def send_escalation_notification(requisition, escalation_reason):
    """
    Send notification when approval is escalated.
    """
    if not is_approval_escalation_email_notifications_enabled():
        return
    
    try:
        recipients = get_approval_escalation_alert_recipients()
        if not recipients:
            recipients = [requisition.requested_by.email]  # Fallback to requester
        
        subject = f"Approval Escalated: {requisition.transaction_id}"
        message = f"""
Approval Escalation Alert:

Transaction ID: {requisition.transaction_id}
Requester: {requisition.requested_by.get_full_name()}
Amount: {requisition.amount}
Escalation Reason: {escalation_reason}

The approval has been escalated due to: {escalation_reason}

Please review this escalated approval.

Best regards,
Petty Cash System
"""
        
        from django.core.mail import send_mail
        from workflow.services.resolver import get_system_email_from
        
        send_mail(
            subject=subject,
            message=message,
            from_email=get_system_email_from(),
            recipient_list=recipients,
            fail_silently=True,
        )
        
        logger.info(f"Escalation notification sent for {requisition.transaction_id}")
        
    except Exception as e:
        logger.error(f"Failed to send escalation notification: {e}")


def send_sla_breach_notification(requisition, breach_type):
    """
    Send notification when SLA is breached.
    """
    if not is_sla_breach_email_notifications_enabled():
        return
    
    try:
        recipients = get_sla_breach_alert_recipients()
        if not recipients:
            # Fallback to requester and next approver
            recipients = [requisition.requested_by.email]
            if requisition.next_approver:
                recipients.append(requisition.next_approver.email)
        
        subject = f"SLA Breach Alert: {requisition.transaction_id}"
        message = f"""
SLA Breach Alert:

Transaction ID: {requisition.transaction_id}
Requester: {requisition.requested_by.get_full_name()}
Amount: {requisition.amount}
Breach Type: {breach_type}
Current Status: {requisition.status}

This requisition has breached its SLA deadline. Immediate attention required.

Best regards,
Petty Cash System
"""
        
        from django.core.mail import send_mail
        from workflow.services.resolver import get_system_email_from
        
        send_mail(
            subject=subject,
            message=message,
            from_email=get_system_email_from(),
            recipient_list=recipients,
            fail_silently=True,
        )
        
        logger.info(f"SLA breach notification sent for {requisition.transaction_id}")
        
    except Exception as e:
        logger.error(f"Failed to send SLA breach notification: {e}")


def send_payment_notification(payment, notification_type):
    """
    Send notification for payment events.
    notification_type: 'executed', 'failed', 'reconciled', 'replenishment_needed'
    """
    if not is_payment_email_notifications_enabled():
        return
    
    try:
        from treasury.models import Payment
        
        # Determine recipients based on notification type
        recipients = []
        
        if notification_type == 'executed':
            # Notify requester and executor
            recipients = [payment.requisition.requested_by.email]
            if payment.executor and payment.executor.email != payment.requisition.requested_by.email:
                recipients.append(payment.executor.email)
        elif notification_type == 'failed':
            # Notify executor and treasury team
            recipients = [payment.executor.email] if payment.executor else []
            treasury_recipients = get_system_maintenance_alert_recipients()
            recipients.extend(treasury_recipients)
        elif notification_type == 'reconciled':
            # Notify requester and executor
            recipients = [payment.requisition.requested_by.email]
            if payment.executor and payment.executor.email != payment.requisition.requested_by.email:
                recipients.append(payment.executor.email)
        elif notification_type == 'replenishment_needed':
            # Notify treasury team
            recipients = get_system_maintenance_alert_recipients()
        
        if not recipients:
            return
        
        # Create subject and message based on type
        if notification_type == 'executed':
            subject = f"Payment Executed: {payment.requisition.transaction_id}"
            message = f"""
Payment Executed Successfully:

Transaction ID: {payment.requisition.transaction_id}
Payment ID: {payment.payment_id}
Requester: {payment.requisition.requested_by.get_full_name()}
Amount: {payment.amount}
Method: {payment.method}
Executor: {payment.executor.get_full_name() if payment.executor else 'System'}

Your payment has been processed successfully.

Best regards,
Petty Cash System
"""
        elif notification_type == 'failed':
            subject = f"Payment Failed: {payment.requisition.transaction_id}"
            message = f"""
Payment Execution Failed:

Transaction ID: {payment.requisition.transaction_id}
Payment ID: {payment.payment_id}
Requester: {payment.requisition.requested_by.get_full_name()}
Amount: {payment.amount}
Method: {payment.method}
Error: {payment.last_error or 'Unknown error'}

Please contact the treasury team for assistance.

Best regards,
Petty Cash System
"""
        elif notification_type == 'reconciled':
            subject = f"Payment Reconciled: {payment.requisition.transaction_id}"
            message = f"""
Payment Reconciliation Complete:

Transaction ID: {payment.requisition.transaction_id}
Payment ID: {payment.payment_id}
Requester: {payment.requisition.requested_by.get_full_name()}
Amount: {payment.amount}
Method: {payment.method}

Your payment has been reconciled and confirmed.

Best regards,
Petty Cash System
"""
        elif notification_type == 'replenishment_needed':
            subject = f"Treasury Fund Replenishment Required"
            message = f"""
Treasury Fund Replenishment Alert:

Fund: {payment.requisition.company} - {payment.requisition.region} - {payment.requisition.branch}
Current Balance: Low
Recent Payment: {payment.payment_id} for {payment.amount}

The treasury fund balance is below the reorder level. Please initiate replenishment.

Best regards,
Petty Cash System
"""
        
        from django.core.mail import send_mail
        from workflow.services.resolver import get_system_email_from
        
        send_mail(
            subject=subject,
            message=message,
            from_email=get_system_email_from(),
            recipient_list=recipients,
            fail_silently=True,
        )
        
        logger.info(f"Payment notification ({notification_type}) sent for {payment.payment_id}")
        
    except Exception as e:
        logger.error(f"Failed to send payment notification: {e}")


def send_rejection_notification(requisition, rejection_reason):
    """
    Send notification when requisition is rejected.
    """
    if not is_rejection_email_notifications_enabled():
        return
    
    try:
        recipients = [requisition.requested_by.email]
        
        subject = f"Requisition Rejected: {requisition.transaction_id}"
        message = f"""
Requisition Rejection Notice:

Transaction ID: {requisition.transaction_id}
Requester: {requisition.requested_by.get_full_name()}
Amount: {requisition.amount}
Rejected By: {requisition.rejected_by.get_full_name() if requisition.rejected_by else 'System'}
Rejection Reason: {rejection_reason}

Your requisition has been rejected. Please review the reason and resubmit if necessary.

Best regards,
Petty Cash System
"""
        
        from django.core.mail import send_mail
        from workflow.services.resolver import get_system_email_from
        
        send_mail(
            subject=subject,
            message=message,
            from_email=get_system_email_from(),
            recipient_list=recipients,
            fail_silently=True,
        )
        
        logger.info(f"Rejection notification sent for {requisition.transaction_id}")
        
    except Exception as e:
        logger.error(f"Failed to send rejection notification: {e}")


def send_system_maintenance_notification(subject, message, recipients=None):
    """
    Send system maintenance notifications.
    """
    if not is_system_maintenance_email_notifications_enabled():
        return
    
    try:
        if recipients is None:
            recipients = get_system_maintenance_alert_recipients()
        
        if not recipients:
            return
        
        from django.core.mail import send_mail
        from workflow.services.resolver import get_system_email_from
        
        send_mail(
            subject=subject,
            message=message,
            from_email=get_system_email_from(),
            recipient_list=recipients,
            fail_silently=True,
        )
        
        logger.info(f"System maintenance notification sent: {subject}")
        
    except Exception as e:
        logger.error(f"Failed to send system maintenance notification: {e}")
