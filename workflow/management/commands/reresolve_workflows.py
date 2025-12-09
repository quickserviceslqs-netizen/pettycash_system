"""
Re-resolve workflows for pending requisitions.
This fixes requisitions that have incorrect next_approver assignments.
"""

from django.core.management.base import BaseCommand
from transactions.models import Requisition
from workflow.services.resolver import resolve_workflow


class Command(BaseCommand):
    help = "Re-resolve workflows for pending requisitions to fix next_approver"

    def handle(self, *args, **options):
        pending_reqs = Requisition.objects.filter(status="pending")

        fixed_count = 0
        for req in pending_reqs:
            try:
                # Re-resolve the workflow
                resolve_workflow(req)
                fixed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Fixed {req.transaction_id}: next_approver = {req.next_approver}"
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Error fixing {req.transaction_id}: {str(e)}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Re-resolved {fixed_count} pending requisitions")
        )
