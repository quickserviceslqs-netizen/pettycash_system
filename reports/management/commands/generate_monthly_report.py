"""
Management command to generate monthly reports automatically.
"""
import os
import csv
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from django.conf import settings
from django.core.mail import send_mail
from transactions.models import Requisition, ApprovalTrail
from treasury.models import Payment, TreasuryFund
from django.contrib.auth import get_user_model
from workflow.services.resolver import (
    is_auto_generate_monthly_reports_enabled, get_report_email_recipients,
    get_financial_year_start_month, get_report_timezone
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate monthly reports automatically if enabled'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force generation even if auto-generation is disabled',
        )
        parser.add_argument(
            '--month',
            type=int,
            help='Month to generate report for (1-12). Defaults to previous month',
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Year to generate report for. Defaults to current year',
        )

    def handle(self, *args, **options):
        if not is_auto_generate_monthly_reports_enabled() and not options['force']:
            self.stdout.write('Auto-generation of monthly reports is disabled. Use --force to override.')
            return

        # Determine report period
        now = timezone.now()
        if options['month'] and options['year']:
            report_year = options['year']
            report_month = options['month']
        else:
            # Default to previous month
            last_month = now - timedelta(days=30)
            report_year = last_month.year
            report_month = last_month.month

        # Calculate date range for the month
        start_date = datetime(report_year, report_month, 1)
        if report_month == 12:
            end_date = datetime(report_year + 1, 1, 1)
        else:
            end_date = datetime(report_year, report_month + 1, 1)

        self.stdout.write(f'Generating monthly report for {start_date.strftime("%B %Y")}')

        # Generate report data
        report_data = self.generate_report_data(start_date, end_date)

        # Save report to file
        filename = f'monthly_report_{report_year}_{report_month:02d}.csv'
        filepath = os.path.join(settings.MEDIA_ROOT, 'reports', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Metric', 'Value'])
            for key, value in report_data.items():
                writer.writerow([key, value])

        self.stdout.write(f'Report saved to {filepath}')

        # Send email notification
        recipients = get_report_email_recipients()
        if recipients:
            self.send_report_email(filename, report_data, recipients)

        self.stdout.write('Monthly report generation completed successfully')

    def generate_report_data(self, start_date, end_date):
        """Generate comprehensive monthly report data"""
        # Convert to timezone-aware datetimes
        start_datetime = timezone.make_aware(start_date)
        end_datetime = timezone.make_aware(end_date)

        # Transaction Statistics
        requisitions = Requisition.objects.filter(
            created_at__gte=start_datetime,
            created_at__lt=end_datetime
        )

        transaction_stats = {
            'total_requisitions': requisitions.count(),
            'total_amount': requisitions.aggregate(Sum('amount'))['amount__sum'] or 0,
            'pending_requisitions': requisitions.filter(status__in=['pending', 'pending_urgency_confirmation', 'change_requested']).count(),
            'approved_requisitions': requisitions.filter(status='approved').count(),
            'rejected_requisitions': requisitions.filter(status='rejected').count(),
            'paid_requisitions': requisitions.filter(status='paid').count(),
        }

        # Treasury Statistics
        treasury_stats = {
            'total_treasury_balance': TreasuryFund.objects.aggregate(Sum('current_balance'))['current_balance__sum'] or 0,
            'funds_below_reorder': TreasuryFund.objects.filter(current_balance__lt=models.F('reorder_level')).count(),
        }

        # Payment Statistics
        payments = Payment.objects.filter(
            requisition__created_at__gte=start_datetime,
            requisition__created_at__lt=end_datetime
        )

        payment_stats = {
            'total_payments': payments.count(),
            'successful_payments': payments.filter(status='success').count(),
            'failed_payments': payments.filter(status='failed').count(),
            'total_paid_amount': payments.filter(status='success').aggregate(Sum('amount'))['amount__sum'] or 0,
        }

        # Approval Statistics
        approvals = ApprovalTrail.objects.filter(
            timestamp__gte=start_datetime,
            timestamp__lt=end_datetime
        )

        approval_stats = {
            'total_approvals': approvals.filter(action='approved').count(),
            'total_rejections': approvals.filter(action='rejected').count(),
            'total_change_requests': approvals.filter(action='changes_requested').count(),
        }

        # User Activity
        user_stats = {
            'active_users': requisitions.values('requested_by').distinct().count(),
            'total_approvers': approvals.values('user').distinct().count(),
        }

        # Combine all stats
        report_data = {}
        report_data.update({f'transaction_{k}': v for k, v in transaction_stats.items()})
        report_data.update({f'treasury_{k}': v for k, v in treasury_stats.items()})
        report_data.update({f'payment_{k}': v for k, v in payment_stats.items()})
        report_data.update({f'approval_{k}': v for k, v in approval_stats.items()})
        report_data.update({f'user_{k}': v for k, v in user_stats.items()})

        return report_data

    def send_report_email(self, filename, report_data, recipients):
        """Send report via email"""
        subject = f'Monthly Report - {datetime.now().strftime("%B %Y")}'

        # Create summary message
        message = f"""
Monthly Report Summary
======================

Period: {datetime.now().strftime("%B %Y")}

Key Metrics:
- Total Requisitions: {report_data.get('transaction_total_requisitions', 0)}
- Total Amount: ${report_data.get('transaction_total_amount', 0):,.2f}
- Successful Payments: {report_data.get('payment_successful_payments', 0)}
- Treasury Balance: ${report_data.get('treasury_total_treasury_balance', 0):,.2f}

The full report has been attached.

This is an automated monthly report.
"""

        # Send email with attachment
        from django.core.mail import EmailMessage
        from workflow.services.resolver import get_system_email_from

        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=get_system_email_from(),
            to=recipients,
        )

        # Attach the report file
        filepath = os.path.join(settings.MEDIA_ROOT, 'reports', filename)
        if os.path.exists(filepath):
            email.attach_file(filepath)

        email.send()

        self.stdout.write(f'Report email sent to {", ".join(recipients)}')