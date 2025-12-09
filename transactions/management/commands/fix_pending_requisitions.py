"""
Management command to fix pending requisitions with missing next_approver.
Run this after deploying the role-matching fix.
"""

from django.core.management.base import BaseCommand
from transactions.models import Requisition


class Command(BaseCommand):
    help = "Fix pending requisitions that have missing next_approver due to role-matching bug"

    def handle(self, *args, **options):
        # Find pending requisitions without next_approver
        broken_requisitions = Requisition.objects.filter(
            status="pending", next_approver__isnull=True
        )

        count = broken_requisitions.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("✅ No broken requisitions found"))
            return

        self.stdout.write(f"Found {count} requisition(s) with missing next_approver")

        fixed = 0
        failed = 0

        for req in broken_requisitions:
            try:
                # Re-resolve workflow with fixed role matching
                req.resolve_workflow()
                self.stdout.write(f"✅ Fixed requisition {req.transaction_id}")
                fixed += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Failed to fix {req.transaction_id}: {str(e)}")
                )
                failed += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Summary: {fixed} fixed, {failed} failed")
        )
