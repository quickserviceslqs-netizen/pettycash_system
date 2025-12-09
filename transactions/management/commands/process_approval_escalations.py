"""
Management command to process approval escalations and notifications
Run this periodically (e.g., hourly) via cron/scheduler
"""

from datetime import timedelta

from django.conf import settings as django_settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from settings_manager.models import get_setting
from transactions.models import ApprovalTrail, Requisition


class Command(BaseCommand):
    help = "Process approval escalations and send notifications for pending approvals"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )

        # Check if features are enabled
        escalation_enabled = get_setting("APPROVAL_ESCALATION_ENABLED", True)
        notification_enabled = get_setting("APPROVAL_NOTIFICATION_ENABLED", True)
        deadline_hours = get_setting("DEFAULT_APPROVAL_DEADLINE_HOURS", 24)
        max_approvals = get_setting("MAX_APPROVALS_PER_REQUISITION", 10)

        self.stdout.write(f"\nSettings:")
        self.stdout.write(f"  Escalation Enabled: {escalation_enabled}")
        self.stdout.write(f"  Notifications Enabled: {notification_enabled}")
        self.stdout.write(f"  Deadline Hours: {deadline_hours}")
        self.stdout.write(f"  Max Approvals: {max_approvals}")

        # Get pending requisitions
        pending_reqs = Requisition.objects.filter(status="pending")
        self.stdout.write(f"\nFound {pending_reqs.count()} pending requisitions")

        escalated_count = 0
        notified_count = 0
        max_approvals_count = 0

        for req in pending_reqs:
            # Check approval count limit
            approval_count = ApprovalTrail.objects.filter(
                requisition=req, action="approved"
            ).count()

            if approval_count >= max_approvals:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠️  {req.transaction_id}: Exceeded max approvals ({approval_count}/{max_approvals})"
                    )
                )
                max_approvals_count += 1
                continue

            # Check if approval is overdue
            if req.created_at:
                time_pending = timezone.now() - req.created_at
                deadline = timedelta(hours=deadline_hours)

                if time_pending > deadline:
                    # Handle escalation
                    if escalation_enabled:
                        if not dry_run:
                            # Create escalation trail entry
                            ApprovalTrail.objects.create(
                                requisition=req,
                                user=None,
                                role="system",
                                action="approved",  # Auto-approve to escalate
                                comment=f"Auto-escalated after {deadline_hours} hours",
                                auto_escalated=True,
                                escalation_reason=f"Exceeded {deadline_hours}h deadline",
                            )
                            escalated_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"  ✅ {req.transaction_id}: Escalated (pending {time_pending.total_seconds()/3600:.1f}h)"
                                )
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"  [DRY RUN] Would escalate: {req.transaction_id}"
                                )
                            )

                    # Send notification
                    if notification_enabled and req.next_approver:
                        if not dry_run:
                            self._send_overdue_notification(req, time_pending)
                            notified_count += 1
                        else:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"  [DRY RUN] Would notify: {req.next_approver.email}"
                                )
                            )

        # Summary
        self.stdout.write(f'\n{"-"*60}')
        self.stdout.write(self.style.SUCCESS(f"Summary:"))
        self.stdout.write(f"  Escalated: {escalated_count}")
        self.stdout.write(f"  Notifications sent: {notified_count}")
        self.stdout.write(f"  Max approvals exceeded: {max_approvals_count}")
        self.stdout.write(f'{"-"*60}\n')

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN COMPLETE - No changes made"))

    def _send_overdue_notification(self, requisition, time_pending):
        """Send email notification for overdue approval"""
        try:
            hours_pending = time_pending.total_seconds() / 3600

            subject = f"Overdue Approval: {requisition.transaction_id}"
            message = f"""
Hello {requisition.next_approver.get_full_name()},

The following requisition requires your approval and is overdue:

Transaction ID: {requisition.transaction_id}
Requested by: {requisition.requested_by.get_full_name()}
Amount: {requisition.amount}
Purpose: {requisition.purpose}
Pending for: {hours_pending:.1f} hours

Please review and approve/reject at your earliest convenience.

Thank you.
            """

            send_mail(
                subject,
                message,
                django_settings.DEFAULT_FROM_EMAIL,
                [requisition.next_approver.email],
                fail_silently=True,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"  📧 Sent notification to {requisition.next_approver.email}"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"  ❌ Failed to send notification: {str(e)}")
            )
