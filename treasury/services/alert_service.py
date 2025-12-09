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
        notify_emails=None,
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

        # Send email notification if emails provided
        if notify_emails:
            AlertService.send_alert_email(alert, notify_emails)

        return alert

    @staticmethod
    def check_fund_critical(fund):
        """
        Check if fund balance is critical (< 80% of reorder level).
        Create alert if critical and no existing unresolved alert.
        """
        # Use Decimal arithmetic to avoid mixing Decimal and float
        if fund.current_balance < (fund.reorder_level * Decimal("0.8")):
            # Check for existing unresolved alert
            existing = Alert.objects.filter(
                alert_type="fund_critical", related_fund=fund, resolved_at__isnull=True
            ).exists()

            if not existing:
                return AlertService.create_alert(
                    alert_type="fund_critical",
                    severity="Critical",
                    title=f"Fund Balance Critical: {fund.company.name} - {fund}",
                    message=f"Fund balance {float(fund.current_balance)} is below 80% of reorder level {float(fund.reorder_level)}",
                    related_fund=fund,
                    notify_emails=["treasury@company.com", "finance@company.com"],
                )
        return None

    @staticmethod
    def check_fund_low(fund):
        """
        Check if fund balance is low (< reorder level but > 80%).
        Create alert if low and no existing unresolved alert.
        """
        if (fund.current_balance < fund.reorder_level) and (
            fund.current_balance >= (fund.reorder_level * Decimal("0.8"))
        ):
            # Check for existing unresolved alert
            existing = Alert.objects.filter(
                alert_type="fund_low", related_fund=fund, resolved_at__isnull=True
            ).exists()

            if not existing:
                return AlertService.create_alert(
                    alert_type="fund_low",
                    severity="High",
                    title=f"Fund Balance Low: {fund.company.name} - {fund}",
                    message=f"Fund balance {float(fund.current_balance)} is below reorder level {float(fund.reorder_level)}. Consider replenishment.",
                    related_fund=fund,
                    notify_emails=["finance-manager@company.com"],
                )
        return None

    @staticmethod
    def check_payment_failed(payment, retry_count, max_retries):
        """
        Check if payment has failed after max retries.
        """
        if retry_count >= max_retries:
            existing = Alert.objects.filter(
                alert_type="payment_failed",
                related_payment=payment,
                resolved_at__isnull=True,
            ).exists()

            if not existing:
                return AlertService.create_alert(
                    alert_type="payment_failed",
                    severity="Critical",
                    title=f"Payment Failed (Max Retries): {payment.payment_id}",
                    message=f"Payment {payment.payment_id} for {payment.requisition} failed after {max_retries} retries. Manual intervention required.",
                    related_payment=payment,
                    notify_emails=["treasury@company.com", "manager@company.com"],
                )
        return None

    @staticmethod
    def check_payment_timeout(payment, execution_time_minutes=None):
        """
        Check if payment execution is taking too long.
        """
        from django.utils.timezone import now
        from datetime import timedelta
        from settings_manager.models import SystemSetting

        if execution_time_minutes is None:
            execution_time_minutes = SystemSetting.get_setting(
                "PAYMENT_EXECUTION_TIMEOUT_MINUTES", 60
            )

        if payment.status == "executing":
            if (now() - payment.execution_timestamp) > timedelta(
                minutes=execution_time_minutes
            ):
                existing = Alert.objects.filter(
                    alert_type="payment_timeout",
                    related_payment=payment,
                    resolved_at__isnull=True,
                ).exists()

                if not existing:
                    return AlertService.create_alert(
                        alert_type="payment_timeout",
                        severity="High",
                        title=f"Payment Execution Timeout: {payment.payment_id}",
                        message=f"Payment {payment.payment_id} has been in executing state for {execution_time_minutes}+ minutes. Check gateway status.",
                        related_payment=payment,
                        notify_emails=["treasury@company.com"],
                    )
        return None

    @staticmethod
    def check_otp_expired(payment):
        """
        Check if OTP has expired.
        """
        from django.utils.timezone import now
        from datetime import timedelta
        from settings_manager.models import SystemSetting

        otp_expiry_minutes = SystemSetting.get_setting("PAYMENT_OTP_EXPIRY_MINUTES", 5)

        if payment.otp_sent_timestamp and not payment.otp_verified:
            if (now() - payment.otp_sent_timestamp) > timedelta(
                minutes=otp_expiry_minutes
            ):
                existing = Alert.objects.filter(
                    alert_type="otp_expired",
                    related_payment=payment,
                    resolved_at__isnull=True,
                ).exists()

                if not existing:
                    return AlertService.create_alert(
                        alert_type="otp_expired",
                        severity="Medium",
                        title=f"OTP Expired: {payment.payment_id}",
                        message=f"OTP for payment {payment.payment_id} has expired. User should request new OTP.",
                        related_payment=payment,
                    )
        return None

    @staticmethod
    def check_variance_pending(variance, threshold_hours=None):
        """
        Check if variance has been pending approval for too long.
        """
        from django.utils.timezone import now
        from datetime import timedelta
        from settings_manager.models import SystemSetting

        if threshold_hours is None:
            threshold_hours = SystemSetting.get_setting(
                "VARIANCE_APPROVAL_DEADLINE_HOURS", 24
            )

        if variance.status == "pending":
            if (now() - variance.created_at) > timedelta(hours=threshold_hours):
                existing = Alert.objects.filter(
                    alert_type="variance_pending",
                    related_variance=variance,
                    resolved_at__isnull=True,
                ).exists()

                if not existing:
                    return AlertService.create_alert(
                        alert_type="variance_pending",
                        severity="Medium",
                        title=f"Variance Pending CFO Approval: {variance.adjustment_id}",
                        message=f"Variance of {float(variance.variance_amount)} has been pending approval for {threshold_hours}+ hours.",
                        related_variance=variance,
                        notify_emails=["cfo@company.com"],
                    )
        return None

    @staticmethod
    def check_replenishment_auto_trigger(fund, replenishment_request):
        """
        Alert when replenishment is auto-triggered due to low balance.
        """
        return AlertService.create_alert(
            alert_type="replenishment_auto",
            severity="High",
            title=f"Automatic Replenishment Triggered: {fund}",
            message=f"Replenishment auto-triggered for {fund} due to balance falling below reorder level. Amount requested: {float(replenishment_request.requested_amount)}",
            related_fund=fund,
            notify_emails=["finance-manager@company.com", "treasury@company.com"],
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
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "title": alert.title,
                "message": alert.message,
                "created_at": alert.created_at,
                "related_payment": alert.related_payment,
                "related_fund": alert.related_fund,
                "related_variance": alert.related_variance,
            }

            html_message = render_to_string("emails/alert_notification.html", context)
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
            alert.save(update_fields=["email_sent", "email_sent_at"])

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
            query = (
                query.filter(related_fund__company_id=company_id)
                | query.filter(related_payment__requisition__company_id=company_id)
                | query.filter(related_variance__treasury_fund__company_id=company_id)
            )

        if severity:
            query = query.filter(severity=severity)

        if alert_type:
            query = query.filter(alert_type=alert_type)

        return query.order_by("-created_at")

    @staticmethod
    def get_alert_summary(company_id=None):
        """
        Get summary of alerts by severity.
        """
        query = Alert.objects.filter(resolved_at__isnull=True)

        if company_id:
            query = (
                query.filter(related_fund__company_id=company_id)
                | query.filter(related_payment__requisition__company_id=company_id)
                | query.filter(related_variance__treasury_fund__company_id=company_id)
            )

        summary = {
            "Critical": query.filter(severity="Critical").count(),
            "High": query.filter(severity="High").count(),
            "Medium": query.filter(severity="Medium").count(),
            "Low": query.filter(severity="Low").count(),
            "Total": query.count(),
        }

        return summary
