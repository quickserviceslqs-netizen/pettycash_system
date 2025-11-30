"""
Alert Service - Manages alert creation, triggering, and email notifications.
"""

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from treasury.models import Alert, TreasuryFund, Payment, VarianceAdjustment
from decimal import Decimal


class AlertService:
    """
    Service for creating and managing treasury alerts.
    """
    
    @staticmethod
    def create_alert(
        alert_type,
        severity,
        title,
        message,
        related_payment=None,
        related_fund=None,
        related_variance=None,
        notify_emails=None
    ):
        """
        Create an alert and send email notification.
        """
        alert = Alert.objects.create(
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            related_payment=related_payment,
            related_fund=related_fund,
            related_variance=related_variance,
        )
        
        # Wire notification settings from SystemSetting
        from settings_manager.models import get_setting
        # Determine notification type and setting key
        notification_map = {
            'fund_critical': ('FUND_CRITICAL_EMAIL_NOTIFICATIONS', 'FUND_CRITICAL_ALERT_RECIPIENTS'),
            'fund_low': ('FUND_LOW_EMAIL_NOTIFICATIONS', 'FUND_LOW_ALERT_RECIPIENTS'),
            'payment_failed': ('PAYMENT_EMAIL_NOTIFICATIONS', 'PAYMENT_ALERT_RECIPIENTS'),
            'payment_timeout': ('PAYMENT_EMAIL_NOTIFICATIONS', 'PAYMENT_ALERT_RECIPIENTS'),
            'otp_expired': ('PAYMENT_EMAIL_NOTIFICATIONS', 'PAYMENT_ALERT_RECIPIENTS'),
            'variance_pending': ('APPROVAL_EMAIL_NOTIFICATIONS', 'APPROVAL_ALERT_RECIPIENTS'),
            'replenishment_auto': ('PAYMENT_EMAIL_NOTIFICATIONS', 'PAYMENT_ALERT_RECIPIENTS'),
            'approval_escalation': ('APPROVAL_ESCALATION_EMAIL_NOTIFICATIONS', 'APPROVAL_ESCALATION_ALERT_RECIPIENTS'),
            'sla_breach': ('SLA_BREACH_EMAIL_NOTIFICATIONS', 'SLA_BREACH_ALERT_RECIPIENTS'),
            'overdue': ('SEND_OVERDUE_ALERTS', 'OVERDUE_ALERT_RECIPIENTS'),
            'critical_overdue': ('SEND_CRITICAL_OVERDUE_ALERTS', 'CRITICAL_OVERDUE_ALERT_RECIPIENTS'),
            'security_alert': ('SECURITY_ALERT_EMAIL_NOTIFICATIONS', 'SECURITY_ALERT_RECIPIENTS'),
            'fraud_alert': ('FRAUD_ALERT_EMAIL_NOTIFICATIONS', 'FRAUD_ALERT_RECIPIENTS'),
            'system_maintenance': ('SYSTEM_MAINTENANCE_EMAIL_NOTIFICATIONS', 'SYSTEM_MAINTENANCE_ALERT_RECIPIENTS'),
        }
        notif_type = alert_type if alert_type in notification_map else None
        send_email = True
        recipients = notify_emails if notify_emails else []
        if notif_type:
            notif_setting_key, recipient_setting_key = notification_map[notif_type]
            send_email = get_setting(notif_setting_key, True)
            recipient_str = get_setting(recipient_setting_key, None)
            if recipient_str:
                recipients = [e.strip() for e in recipient_str.split(',') if e.strip()]
        if send_email and recipients:
            AlertService.send_alert_email(alert, recipients)
        
        return alert
    
    @staticmethod
    def check_fund_critical(fund):
        """
        Check if fund balance is critical based on configured alert percentage.
        Create alert if critical and no existing unresolved alert.
        """
        from settings_manager.models import get_setting
        
        # Get alert percentage from settings
        alert_percentage = Decimal(get_setting('TREASURY_LOW_BALANCE_ALERT_PERCENTAGE', '100'))
        threshold = fund.reorder_level * (alert_percentage / 100)
        
        if fund.current_balance < threshold:
            # Check for existing unresolved alert
            existing = Alert.objects.filter(
                alert_type='fund_critical',
                related_fund=fund,
                resolved_at__isnull=True
            ).exists()
            
            if not existing:
                return AlertService.create_alert(
                    alert_type='fund_critical',
                    severity='Critical',
                    title=f'Fund Balance Critical: {fund.company.name} - {fund}',
                    message=f'Fund balance {float(fund.current_balance)} is below {alert_percentage}% of reorder level {float(fund.reorder_level)}',
                    related_fund=fund,
                    notify_emails=['treasury@company.com', 'finance@company.com']
                )
        return None
    
    @staticmethod
    def check_fund_low(fund):
        """
        Check if fund balance is low based on configured alert threshold.
        Create alert if low and no existing unresolved alert.
        """
        from settings_manager.models import get_setting
        
        # Get alert threshold from settings
        alert_threshold = Decimal(get_setting('LOW_BALANCE_ALERT_THRESHOLD', '50000'))
        
        if fund.current_balance < alert_threshold:
            # Check for existing unresolved alert
            existing = Alert.objects.filter(
                alert_type='fund_low',
                related_fund=fund,
                resolved_at__isnull=True
            ).exists()
            
            if not existing:
                return AlertService.create_alert(
                    alert_type='fund_low',
                    severity='High',
                    title=f'Fund Balance Low: {fund.company.name} - {fund}',
                    message=f'Fund balance {float(fund.current_balance)} is below alert threshold {float(alert_threshold)}. Consider replenishment.',
                    related_fund=fund,
                    notify_emails=['finance-manager@company.com']
                )
        return None
    
    @staticmethod
    def check_payment_failed(payment, retry_count, max_retries):
        """
        Check if payment has failed after max retries.
        """
        if retry_count >= max_retries:
            existing = Alert.objects.filter(
                alert_type='payment_failed',
                related_payment=payment,
                resolved_at__isnull=True
            ).exists()
            
            if not existing:
                return AlertService.create_alert(
                    alert_type='payment_failed',
                    severity='Critical',
                    title=f'Payment Failed (Max Retries): {payment.payment_id}',
                    message=f'Payment {payment.payment_id} for {payment.requisition} failed after {max_retries} retries. Manual intervention required.',
                    related_payment=payment,
                    notify_emails=['treasury@company.com', 'manager@company.com']
                )
        return None
    
    @staticmethod
    def check_payment_timeout(payment, execution_time_minutes=60):
        """
        Check if payment execution is taking too long.
        """
        from django.utils.timezone import now
        from datetime import timedelta
        
        if payment.status == 'executing':
            if (now() - payment.execution_timestamp) > timedelta(minutes=execution_time_minutes):
                existing = Alert.objects.filter(
                    alert_type='payment_timeout',
                    related_payment=payment,
                    resolved_at__isnull=True
                ).exists()
                
                if not existing:
                    return AlertService.create_alert(
                        alert_type='payment_timeout',
                        severity='High',
                        title=f'Payment Execution Timeout: {payment.payment_id}',
                        message=f'Payment {payment.payment_id} has been in executing state for {execution_time_minutes}+ minutes. Check gateway status.',
                        related_payment=payment,
                        notify_emails=['treasury@company.com']
                    )
        return None
    
    @staticmethod
    def check_otp_expired(payment):
        """
        Check if OTP has expired (> 5 minutes).
        """
        from django.utils.timezone import now
        from datetime import timedelta
        
        if payment.otp_sent_timestamp and not payment.otp_verified:
            if (now() - payment.otp_sent_timestamp) > timedelta(minutes=5):
                existing = Alert.objects.filter(
                    alert_type='otp_expired',
                    related_payment=payment,
                    resolved_at__isnull=True
                ).exists()
                
                if not existing:
                    return AlertService.create_alert(
                        alert_type='otp_expired',
                        severity='Medium',
                        title=f'OTP Expired: {payment.payment_id}',
                        message=f'OTP for payment {payment.payment_id} has expired. User should request new OTP.',
                        related_payment=payment
                    )
        return None
    
    @staticmethod
    def check_variance_pending(variance, threshold_hours=24):
        """
        Check if variance has been pending approval for too long.
        """
        from django.utils.timezone import now
        from datetime import timedelta
        
        if variance.status == 'pending':
            if (now() - variance.created_at) > timedelta(hours=threshold_hours):
                existing = Alert.objects.filter(
                    alert_type='variance_pending',
                    related_variance=variance,
                    resolved_at__isnull=True
                ).exists()
                
                if not existing:
                    return AlertService.create_alert(
                        alert_type='variance_pending',
                        severity='Medium',
                        title=f'Variance Pending CFO Approval: {variance.adjustment_id}',
                        message=f'Variance of {float(variance.variance_amount)} has been pending approval for {threshold_hours}+ hours.',
                        related_variance=variance,
                        notify_emails=['cfo@company.com']
                    )
        return None
    
    @staticmethod
    def check_replenishment_auto_trigger(fund, replenishment_request):
        """
        Alert when replenishment is auto-triggered due to low balance.
        """
        return AlertService.create_alert(
            alert_type='replenishment_auto',
            severity='High',
            title=f'Automatic Replenishment Triggered: {fund}',
            message=f'Replenishment auto-triggered for {fund} due to balance falling below reorder level. Amount requested: {float(replenishment_request.requested_amount)}',
            related_fund=fund,
            notify_emails=['finance-manager@company.com', 'treasury@company.com']
        )
    
    @staticmethod
    def send_alert_email(alert, recipient_emails):
        """
        Send alert notification via email.
        """
        try:
            subject = f"[{alert.severity}] {alert.title}"
            
            # Prepare email body
            context = {
                'alert_type': alert.alert_type,
                'severity': alert.severity,
                'title': alert.title,
                'message': alert.message,
                'created_at': alert.created_at,
                'related_payment': alert.related_payment,
                'related_fund': alert.related_fund,
                'related_variance': alert.related_variance,
            }
            
            html_message = render_to_string('emails/alert_notification.html', context)
            plain_message = f"{alert.title}\n\n{alert.message}"
            
            # Send email
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                recipient_emails,
                html_message=html_message,
                fail_silently=True,
            )
            
            # Mark as email sent
            alert.email_sent = True
            alert.email_sent_at = timezone.now()
            alert.save(update_fields=['email_sent', 'email_sent_at'])
            
            return True
        except Exception as e:
            print(f"Error sending alert email: {str(e)}")
            return False
    
    @staticmethod
    def acknowledge_alert(alert, user):
        """
        Acknowledge an alert (mark as seen by user).
        """
        alert.acknowledge(user)
        return alert
    
    @staticmethod
    def resolve_alert(alert, user, notes=None):
        """
        Resolve an alert (mark as handled).
        """
        alert.resolve(user, notes)
        return alert
    
    @staticmethod
    def get_unresolved_alerts(company_id=None, severity=None, alert_type=None):
        """
        Get all unresolved alerts, optionally filtered.
        """
        query = Alert.objects.filter(resolved_at__isnull=True)
        
        if company_id:
            query = query.filter(
                related_fund__company_id=company_id
            ) | query.filter(
                related_payment__requisition__company_id=company_id
            ) | query.filter(
                related_variance__treasury_fund__company_id=company_id
            )
        
        if severity:
            query = query.filter(severity=severity)
        
        if alert_type:
            query = query.filter(alert_type=alert_type)
        
        return query.order_by('-created_at')
    
    @staticmethod
    def get_alert_summary(company_id=None):
        """
        Get summary of alerts by severity.
        """
        query = Alert.objects.filter(resolved_at__isnull=True)
        
        if company_id:
            query = query.filter(
                related_fund__company_id=company_id
            ) | query.filter(
                related_payment__requisition__company_id=company_id
            ) | query.filter(
                related_variance__treasury_fund__company_id=company_id
            )
        
        summary = {
            'Critical': query.filter(severity='Critical').count(),
            'High': query.filter(severity='High').count(),
            'Medium': query.filter(severity='Medium').count(),
            'Low': query.filter(severity='Low').count(),
            'Total': query.count(),
        }
        
        return summary
