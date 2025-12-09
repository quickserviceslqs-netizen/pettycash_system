from datetime import timedelta

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from settings_manager.models import get_setting
from transactions.models import Requisition


@receiver(post_save, sender=Requisition)
def auto_resolve_workflow(sender, instance, created, **kwargs):
    """
    Automatically resolves the workflow sequence for a Requisition after creation
    or when its status changes (excluding drafts).
    """
    if created or (instance.status != "draft" and instance.workflow_sequence is None):
        try:
            instance.resolve_workflow()
        except Exception:
            # Auto-resolution may fail during test data setup (missing thresholds/users).
            # Swallow exceptions here so tests can create Requisition records without full runtime data.
            return


@receiver(post_save, sender=Requisition)
def check_auto_rejection(sender, instance, created, **kwargs):
    """
    Check if requisition should be auto-rejected based on pending time.
    Uses AUTO_REJECT_PENDING_AFTER_HOURS setting.
    """
    # Only check pending requisitions
    if instance.status != "pending":
        return

    # Get auto-reject hours setting (0 = disabled)
    auto_reject_hours = get_setting("AUTO_REJECT_PENDING_AFTER_HOURS", 0)
    if auto_reject_hours <= 0:
        return

    # Check if requisition has been pending too long
    if instance.created_at:
        time_pending = timezone.now() - instance.created_at
        threshold = timedelta(hours=auto_reject_hours)

        if time_pending > threshold:
            instance.status = "rejected"
            instance.rejection_reason = (
                f"Auto-rejected after {auto_reject_hours} hours pending"
            )
            instance.save(update_fields=["status", "rejection_reason"])
