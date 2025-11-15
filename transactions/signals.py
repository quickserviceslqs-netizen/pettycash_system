from django.db.models.signals import post_save
from django.dispatch import receiver
from transactions.models import Requisition

@receiver(post_save, sender=Requisition)
def auto_resolve_workflow(sender, instance, created, **kwargs):
    """
    Automatically resolves the workflow sequence for a Requisition after creation
    or when its status changes (excluding drafts).
    """
    if created or (instance.status != "draft" and instance.workflow_sequence is None):
        instance.resolve_workflow()
