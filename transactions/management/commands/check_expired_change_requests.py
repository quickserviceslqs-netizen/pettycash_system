from django.core.management.base import BaseCommand
from django.utils import timezone
from transactions.models import Requisition, ApprovalTrail
from settings_manager.models import get_setting


class Command(BaseCommand):
    help = 'Check for expired change request deadlines and auto-reject requisitions'

    def handle(self, *args, **options):
        # Check if auto-rejection is enabled
        if not get_setting('AUTO_REJECT_EXPIRED_CHANGES', 'true').lower() == 'true':
            self.stdout.write('Auto-rejection of expired change requests is disabled.')
            return

        now = timezone.now()
        expired_requisitions = Requisition.objects.filter(
            status='change_requested',
            change_request_deadline__lt=now
        ).exclude(change_request_deadline__isnull=True)

        count = 0
        for requisition in expired_requisitions:
            # Auto-reject
            requisition.status = "rejected"
            requisition.next_approver = None
            requisition.workflow_sequence = []
            requisition.save(update_fields=["status", "next_approver", "workflow_sequence"])

            # Create approval trail
            ApprovalTrail.objects.create(
                requisition=requisition,
                user=requisition.change_requested_by,  # The approver who requested changes
                role=requisition.change_requested_by.role if requisition.change_requested_by else 'system',
                action="rejected",
                comment=f"Auto-rejected: Change request deadline expired on {requisition.change_request_deadline.strftime('%B %d, %Y at %I:%M %p')}",
                timestamp=now,
            )

            self.stdout.write(
                self.style.SUCCESS(f'Auto-rejected requisition {requisition.transaction_id} due to expired deadline')
            )
            count += 1

        if count == 0:
            self.stdout.write('No expired change requests found.')
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully auto-rejected {count} requisition(s) with expired change request deadlines.')
            )