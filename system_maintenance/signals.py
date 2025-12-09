"""
Real-time backup signals for automatic backup creation.
"""

from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class RealTimeBackupManager:
    """
    Manager for real-time backup operations.
    Prevents backup loops and manages backup frequency.
    """

    def __init__(self):
        self._last_backup_time = None
        self._backup_cooldown_minutes = getattr(
            settings, "REALTIME_BACKUP_COOLDOWN", 30
        )
        self._is_backing_up = False

    def should_create_backup(self):
        """Check if enough time has passed since last backup"""
        if self._is_backing_up:
            return False

        if self._last_backup_time is None:
            return True

        time_since_last = timezone.now() - self._last_backup_time
        cooldown = timedelta(minutes=self._backup_cooldown_minutes)

        return time_since_last >= cooldown

    def create_realtime_backup(self, reason, user=None):
        """Create a real-time backup if cooldown has passed"""
        if not self.should_create_backup():
            logger.info(
                f"Skipping backup: cooldown active ({self._backup_cooldown_minutes} minutes)"
            )
            return None

        try:
            self._is_backing_up = True

            from system_maintenance.services.backup_service import BackupService
            from system_maintenance.models import BackupRecord

            backup_service = BackupService()
            backup = backup_service.create_backup(
                backup_type="database_only",  # Faster for real-time
                user=user,
                description=f"Real-time backup: {reason}",
            )

            self._last_backup_time = timezone.now()
            logger.info(f"Real-time backup created: {backup.backup_id} - {reason}")

            return backup

        except Exception as e:
            logger.error(f"Real-time backup failed: {str(e)}")
            return None
        finally:
            self._is_backing_up = False


# Global instance
realtime_backup_manager = RealTimeBackupManager()


# ============================================================================
# TRANSACTION SIGNALS - Backup on critical transaction operations
# ============================================================================


@receiver(post_save, sender="transactions.Requisition")
def backup_on_requisition_approved(sender, instance, created, **kwargs):
    """Create backup when requisition is approved (high-value transactions)"""
    # Only backup on approval (not creation)
    if not created and instance.status == "approved":
        # Only backup high-value requisitions
        if instance.amount >= getattr(
            settings, "REALTIME_BACKUP_AMOUNT_THRESHOLD", 10000
        ):
            realtime_backup_manager.create_realtime_backup(
                reason=f"High-value requisition approved: {instance.requisition_id} (${instance.amount})",
                user=instance.approved_by if hasattr(instance, "approved_by") else None,
            )


@receiver(post_delete, sender="transactions.Requisition")
def backup_on_requisition_deleted(sender, instance, **kwargs):
    """Create backup when requisition is deleted"""
    if instance.status in ["approved", "completed"]:
        realtime_backup_manager.create_realtime_backup(
            reason=f"Approved/completed requisition deleted: {instance.requisition_id}",
            user=None,  # Delete signal doesn't have user context
        )


# ============================================================================
# TREASURY SIGNALS - Backup on payment operations
# ============================================================================


@receiver(post_save, sender="treasury.Payment")
def backup_on_payment_created(sender, instance, created, **kwargs):
    """Create backup when payment is created or disbursed"""
    if created or instance.status == "disbursed":
        # Backup on payment creation for high amounts
        if instance.amount >= getattr(
            settings, "REALTIME_BACKUP_AMOUNT_THRESHOLD", 10000
        ):
            realtime_backup_manager.create_realtime_backup(
                reason=f"Payment created/disbursed: {instance.payment_id} (${instance.amount})",
                user=(
                    instance.disbursed_by if hasattr(instance, "disbursed_by") else None
                ),
            )


@receiver(post_delete, sender="treasury.Payment")
def backup_on_payment_deleted(sender, instance, **kwargs):
    """Create backup when payment is deleted"""
    realtime_backup_manager.create_realtime_backup(
        reason=f"Payment deleted: {instance.payment_id} (${instance.amount})", user=None
    )


# ============================================================================
# USER MANAGEMENT SIGNALS - Backup on critical user operations
# ============================================================================


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def backup_on_superuser_created(sender, instance, created, **kwargs):
    """Create backup when superuser is created or modified"""
    if instance.is_superuser:
        if created:
            realtime_backup_manager.create_realtime_backup(
                reason=f"Superuser created: {instance.username}", user=None
            )


@receiver(pre_delete, sender=settings.AUTH_USER_MODEL)
def backup_on_user_deleted(sender, instance, **kwargs):
    """Create backup before user is deleted"""
    if instance.is_superuser or instance.is_staff:
        realtime_backup_manager.create_realtime_backup(
            reason=f"Staff/superuser being deleted: {instance.username}", user=None
        )


# ============================================================================
# SETTINGS SIGNALS - Backup on system settings changes
# ============================================================================


@receiver(post_save, sender="settings_manager.SystemSetting")
def backup_on_critical_setting_changed(sender, instance, created, **kwargs):
    """Create backup when critical system settings are changed"""
    critical_settings = [
        "approval_threshold_manager",
        "approval_threshold_cfo",
        "default_currency",
        "enable_multi_currency",
    ]

    if instance.key in critical_settings:
        realtime_backup_manager.create_realtime_backup(
            reason=f"Critical setting changed: {instance.key} = {instance.value}",
            user=None,
        )


# ============================================================================
# ORGANIZATION SIGNALS - Backup on organizational changes
# ============================================================================


@receiver(post_delete, sender="organization.Company")
def backup_on_company_deleted(sender, instance, **kwargs):
    """Create backup when company is deleted"""
    realtime_backup_manager.create_realtime_backup(
        reason=f"Company deleted: {instance.name}", user=None
    )


@receiver(post_delete, sender="organization.Department")
def backup_on_department_deleted(sender, instance, **kwargs):
    """Create backup when department with users is deleted"""
    # Only backup if department has users
    if hasattr(instance, "users") and instance.users.exists():
        realtime_backup_manager.create_realtime_backup(
            reason=f"Department with users deleted: {instance.name}", user=None
        )


# ============================================================================
# WORKFLOW SIGNALS - Backup on approval threshold changes
# ============================================================================


@receiver(post_save, sender="workflow.ApprovalThreshold")
def backup_on_threshold_changed(sender, instance, created, **kwargs):
    """Create backup when approval thresholds are changed"""
    if not created:  # Only on updates, not creation
        realtime_backup_manager.create_realtime_backup(
            reason=f"Approval threshold modified for {instance.role}", user=None
        )


@receiver(post_delete, sender="workflow.ApprovalThreshold")
def backup_on_threshold_deleted(sender, instance, **kwargs):
    """Create backup when approval threshold is deleted"""
    realtime_backup_manager.create_realtime_backup(
        reason=f"Approval threshold deleted for {instance.role}", user=None
    )
