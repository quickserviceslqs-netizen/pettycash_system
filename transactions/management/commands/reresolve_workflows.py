"""
Management command to re-resolve workflows for pending requisitions.
This fixes requisitions that were created with the old buggy workflow resolver.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from transactions.models import Requisition
from workflow.services.resolver import resolve_workflow


class Command(BaseCommand):
    help = 'Re-resolve workflows for all pending requisitions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        pending_reqs = Requisition.objects.filter(status='pending').order_by('created_at')
        count = pending_reqs.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No pending requisitions found.'))
            return
        
        self.stdout.write(f'Found {count} pending requisition(s)')
        
        fixed = 0
        for req in pending_reqs:
            old_next_approver = req.next_approver.username if req.next_approver else 'None'
            old_workflow_len = len(req.workflow_sequence) if req.workflow_sequence else 0
            
            self.stdout.write(f'\n{req.transaction_id}:')
            self.stdout.write(f'  Amount: {req.amount}, Origin: {req.origin_type}, Branch: {req.branch}')
            self.stdout.write(f'  OLD: next_approver={old_next_approver}, workflow_steps={old_workflow_len}')
            
            if not dry_run:
                with transaction.atomic():
                    # Re-resolve workflow
                    req.applied_threshold = None  # Force re-application
                    req.workflow_sequence = None
                    req.next_approver = None
                    req.save()
                    
                    # Resolve workflow
                    resolve_workflow(req)
            else:
                # Simulate resolution
                from workflow.services.resolver import find_approval_threshold
                threshold = find_approval_threshold(req.amount, req.origin_type)
                if threshold:
                    self.stdout.write(f'  Would use threshold: {threshold.name}')
                    self.stdout.write(f'  Roles: {threshold.roles_sequence}')
            
            # Refresh from DB
            req.refresh_from_db()
            new_next_approver = req.next_approver.username if req.next_approver else 'None'
            new_workflow_len = len(req.workflow_sequence) if req.workflow_sequence else 0
            
            self.stdout.write(self.style.SUCCESS(
                f'  NEW: next_approver={new_next_approver}, workflow_steps={new_workflow_len}'
            ))
            
            if req.workflow_sequence:
                for i, step in enumerate(req.workflow_sequence, 1):
                    user_id = step.get('user_id')
                    role = step.get('role')
                    auto = ' (AUTO-ESCALATED)' if step.get('auto_escalated') else ''
                    self.stdout.write(f'    Step {i}: role={role}, user_id={user_id}{auto}')
            
            if not dry_run:
                fixed += 1
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN - No changes made'))
            self.stdout.write('Run without --dry-run to apply changes')
        else:
            self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully re-resolved {fixed} requisition(s)'))
