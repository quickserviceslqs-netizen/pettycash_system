from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Count, Q, Avg, F
from django.utils import timezone
from datetime import timedelta
from transactions.models import Requisition, ApprovalTrail
from treasury.models import Payment, TreasuryFund
from django.contrib.auth import get_user_model
from workflow.services.resolver import (
    get_report_export_formats, get_report_retention_months, get_report_email_recipients,
    is_auto_generate_monthly_reports_enabled, get_financial_year_start_month,
    is_report_scheduling_enabled, get_report_privacy_level, get_report_access_roles,
    is_report_audit_trail_enabled, is_report_data_masking_enabled,
    get_report_template_choices, get_report_kpi_list, get_report_timezone
)

User = get_user_model()


def is_admin_user(user):
    """Check if user has admin role or is in report access roles"""
    if user.role in ['Admin', 'Super Admin']:
        return True
    
    # Check if user's role is in the allowed report access roles
    allowed_roles = get_report_access_roles()
    return user.role.lower() in [role.lower() for role in allowed_roles]


def is_valid_export_format(format_type):
    """Check if the export format is allowed by settings"""
    allowed_formats = get_report_export_formats()
    return format_type.lower() in [fmt.lower() for fmt in allowed_formats]


def should_mask_data(user):
    """Check if data should be masked for this user"""
    if not is_report_data_masking_enabled():
        return False
    
    # Don't mask for admin/super admin
    if user.role in ['Admin', 'Super Admin']:
        return False
    
    # Mask for users not in privileged roles
    privileged_roles = ['cfo', 'treasury', 'admin']
    return user.role.lower() not in privileged_roles


def log_report_access(user, report_type, action='view'):
    """Log report access for audit trail"""
    if not is_report_audit_trail_enabled():
        return
    
    from settings_manager.models import ActivityLog
    ActivityLog.objects.create(
        user=user,
        action='report_access',
        content_type='Report',
        object_id=report_type,
        description=f'{action.capitalize()} {report_type} report',
    )


@login_required
@user_passes_test(is_admin_user)
def reports_dashboard(request):
    """
    Main reports dashboard with overview metrics and quick access to detailed reports.
    Shows key statistics across transactions, treasury, and approvals.
    """
    # Log report access
    log_report_access(request.user, 'dashboard', 'view')
    # Get date range from request (default: last 30 days)
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # Transaction Statistics
    requisitions = Requisition.objects.filter(created_at__gte=start_date)
    total_requisitions = requisitions.count()
    total_amount = requisitions.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Status breakdown
    status_breakdown = requisitions.values('status').annotate(count=Count('id')).order_by('-count')
    
    # Pending requisitions (not paid, reviewed, or rejected)
    pending_count = requisitions.exclude(status__in=['paid', 'reviewed', 'rejected']).count()
    paid_count = requisitions.filter(status='paid').count()
    rejected_count = requisitions.filter(status='rejected').count()
    
    # Treasury Statistics
    total_treasury_balance = TreasuryFund.objects.aggregate(Sum('current_balance'))['current_balance__sum'] or 0
    funds_below_reorder = TreasuryFund.objects.filter(current_balance__lt=models.F('reorder_level')).count()
    
    # Payment Statistics
    payments = Payment.objects.filter(requisition__created_at__gte=start_date)
    successful_payments = payments.filter(status='success').count()
    failed_payments = payments.filter(status='failed').count()
    total_paid_amount = payments.filter(status='success').aggregate(Sum('amount'))['amount__sum'] or 0
    
    # User Activity
    active_users = requisitions.values('requested_by').distinct().count()
    
    # Approval Metrics
    approval_trails = ApprovalTrail.objects.filter(timestamp__gte=start_date)
    total_approvals = approval_trails.filter(action='approved').count()
    total_rejections = approval_trails.filter(action='rejected').count()
    avg_approval_time = approval_trails.filter(action='approved').aggregate(
        avg_time=Avg(F('timestamp') - F('requisition__created_at'))
    )['avg_time']
    
    # Top requesters
    top_requesters = requisitions.values('requested_by__username', 'requested_by__get_full_name').annotate(
        total=Count('transaction_id'),
        amount=Sum('amount')
    ).order_by('-total')[:5]
    
    # Top approvers
    top_approvers = approval_trails.filter(action='approved').values('user__username').annotate(
        total=Count('id')
    ).order_by('-total')[:5]
    
    from settings_manager.models import get_setting
    context = {
        'days': days,
        'start_date': start_date,
        # Transaction metrics
        'total_requisitions': total_requisitions,
        'total_amount': total_amount,
        'pending_count': pending_count,
        'paid_count': paid_count,
        'rejected_count': rejected_count,
        'status_breakdown': status_breakdown,
        # Treasury metrics
        'total_treasury_balance': total_treasury_balance,
        'funds_below_reorder': funds_below_reorder,
        # Payment metrics
        'successful_payments': successful_payments,
        'failed_payments': failed_payments,
        'total_paid_amount': total_paid_amount,
        # Activity metrics
        'active_users': active_users,
        'total_approvals': total_approvals,
        'total_rejections': total_rejections,
        'avg_approval_time': avg_approval_time,
        # Top users
        'top_requesters': top_requesters,
        'top_approvers': top_approvers,
        # Advanced Reporting Settings
        'report_export_formats': get_report_export_formats(),
        'auto_generate_monthly_reports': is_auto_generate_monthly_reports_enabled(),
        'report_email_recipients': get_report_email_recipients(),
        'financial_year_start_month': get_financial_year_start_month(),
        'report_retention_months': get_report_retention_months(),
        'report_scheduling_enabled': is_report_scheduling_enabled(),
        'report_privacy_level': get_report_privacy_level(),
        'report_access_roles': get_report_access_roles(),
        'enable_report_audit_trail': is_report_audit_trail_enabled(),
        'report_data_masking': is_report_data_masking_enabled(),
        'report_template_choices': get_report_template_choices(),
        'report_kpi_list': get_report_kpi_list(),
        'report_timezone': get_report_timezone(),
    }
    return render(request, 'reports/dashboard.html', context)


@login_required
@user_passes_test(is_admin_user)
def transaction_report(request):
    """
    Detailed transaction/requisition report with filters and export capability.
    """
    # Log report access
    log_report_access(request.user, 'transaction', 'view')
    # Get filter parameters
    days = int(request.GET.get('days', 30))
    status = request.GET.get('status', '')
    branch_id = request.GET.get('branch', '')
    department_id = request.GET.get('department', '')
    min_amount = request.GET.get('min_amount', '')
    max_amount = request.GET.get('max_amount', '')
    
    start_date = timezone.now() - timedelta(days=days)
    
    # Base queryset
    requisitions = Requisition.objects.filter(created_at__gte=start_date).select_related(
        'requested_by', 'branch', 'department', 'cost_center'
    ).order_by('-created_at')
    
    # Apply filters
    if status:
        requisitions = requisitions.filter(status=status)
    if branch_id:
        requisitions = requisitions.filter(branch_id=branch_id)
    if department_id:
        requisitions = requisitions.filter(department_id=department_id)
    if min_amount:
        requisitions = requisitions.filter(amount__gte=min_amount)
    if max_amount:
        requisitions = requisitions.filter(amount__lte=max_amount)
    
    # Statistics
    total_count = requisitions.count()
    total_amount = requisitions.aggregate(Sum('amount'))['amount__sum'] or 0
    avg_amount = requisitions.aggregate(Avg('amount'))['amount__avg'] or 0
    
    # Get unique branches and departments for filters
    from organization.models import Branch, Department
    branches = Branch.objects.all().order_by('name')
    departments = Department.objects.all().order_by('name')
    
    from settings_manager.models import get_setting
    context = {
        'requisitions': requisitions,
        'total_count': total_count,
        'total_amount': total_amount,
        'avg_amount': avg_amount,
        'days': days,
        'selected_status': status,
        'selected_branch': branch_id,
        'selected_department': department_id,
        'min_amount': min_amount,
        'max_amount': max_amount,
        'branches': branches,
        'departments': departments,
        'status_choices': Requisition.STATUS_CHOICES,
        # Reporting settings
        'report_export_formats': get_report_export_formats(),
        'report_retention_months': get_report_retention_months(),
        'report_email_recipients': get_report_email_recipients(),
    }
    return render(request, 'reports/transaction_report.html', context)


@login_required
@user_passes_test(is_admin_user)
def treasury_report(request):
    """
    Treasury fund balances and payment activity report.
    """
    # Log report access
    log_report_access(request.user, 'treasury', 'view')
    # Get all treasury funds with annotations
    funds = TreasuryFund.objects.select_related('company', 'region', 'branch').annotate(
        needs_replenishment=Q(current_balance__lt=F('reorder_level'))
    ).order_by('company', 'region', 'branch')
    
    # Get date range
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # Payment statistics by method
    payment_stats = Payment.objects.filter(
        requisition__created_at__gte=start_date
    ).values('method').annotate(
        count=Count('payment_id'),
        total_amount=Sum('amount')
    ).order_by('-total_amount')
    
    # Payment statistics by status
    status_stats = Payment.objects.filter(
        requisition__created_at__gte=start_date
    ).values('status').annotate(
        count=Count('payment_id'),
        total_amount=Sum('amount')
    ).order_by('-count')
    
    # Overall statistics
    total_balance = funds.aggregate(Sum('current_balance'))['current_balance__sum'] or 0
    funds_needing_replenishment = funds.filter(current_balance__lt=F('reorder_level')).count()
    
    from settings_manager.models import get_setting
    context = {
        'funds': funds,
        'total_balance': total_balance,
        'funds_needing_replenishment': funds_needing_replenishment,
        'payment_stats': payment_stats,
        'status_stats': status_stats,
        'days': days,
        # Reporting settings
        'report_export_formats': get_report_export_formats(),
        'report_retention_months': get_report_retention_months(),
        'report_email_recipients': get_report_email_recipients(),
    }
    return render(request, 'reports/treasury_report.html', context)


@login_required
@user_passes_test(is_admin_user)
def approval_report(request):
    """
    Approval workflow analytics: approval times, bottlenecks, approver performance.
    """
    # Log report access
    log_report_access(request.user, 'approval', 'view')
    # Get date range
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # Approval trails with related data
    approval_trails = ApprovalTrail.objects.filter(
        timestamp__gte=start_date
    ).select_related('user', 'requisition').order_by('-timestamp')
    
    # Approver performance
    approver_stats = approval_trails.values('user__username', 'user__id').annotate(
        total_actions=Count('id'),
        approvals=Count('id', filter=Q(action='approved')),
        rejections=Count('id', filter=Q(action='rejected')),
        change_requests=Count('id', filter=Q(action='changes_requested'))
    ).order_by('-total_actions')
    
    # Action breakdown
    action_breakdown = approval_trails.values('action').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Recent approvals
    recent_approvals = approval_trails[:20]
    
    # Average approval time (time from creation to first approval)
    requisitions_with_approvals = Requisition.objects.filter(
        created_at__gte=start_date,
        status__in=['paid', 'reviewed']
    ).select_related('requested_by')
    
    from settings_manager.models import get_setting
    context = {
        'approval_logs': recent_approvals,
        'approver_stats': approver_stats,
        'action_breakdown': action_breakdown,
        'days': days,
        'total_logs': approval_trails.count(),
        # Reporting settings
        'report_export_formats': get_report_export_formats(),
        'report_retention_months': get_report_retention_months(),
        'report_email_recipients': get_report_email_recipients(),
    }
    return render(request, 'reports/approval_report.html', context)


@login_required
@user_passes_test(is_admin_user)
def user_activity_report(request):
    """
    User activity report: requisition creation, approval actions, payment execution.
    """
    # Log report access
    log_report_access(request.user, 'user_activity', 'view')
    # Get date range
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # User requisition activity
    user_requisition_stats = User.objects.filter(
        requisition__created_at__gte=start_date
    ).annotate(
        total_requisitions=Count('requisition'),
        total_amount_requested=Sum('requisition__amount'),
        pending_count=Count('requisition', filter=Q(requisition__status__in=[
            'pending', 'pending_dept_approval', 'pending_branch_approval',
            'pending_regional_review', 'pending_finance_review',
            'pending_treasury_validation', 'pending_cfo_approval'
        ])),
        paid_count=Count('requisition', filter=Q(requisition__status='paid')),
        rejected_count=Count('requisition', filter=Q(requisition__status='rejected'))
    ).filter(total_requisitions__gt=0).order_by('-total_requisitions')
    
    # User approval activity
    user_approval_stats = User.objects.filter(
        approvaltrail__timestamp__gte=start_date
    ).annotate(
        total_approvals=Count('approvaltrail', filter=Q(approvaltrail__action='approved')),
        total_rejections=Count('approvaltrail', filter=Q(approvaltrail__action='rejected')),
        total_change_requests=Count('approvaltrail', filter=Q(approvaltrail__action='changes_requested'))
    ).filter(
        Q(total_approvals__gt=0) | Q(total_rejections__gt=0) | Q(total_change_requests__gt=0)
    ).order_by('-total_approvals')
    
    # User payment execution activity
    user_payment_stats = User.objects.filter(
        executed_payments__requisition__created_at__gte=start_date
    ).annotate(
        total_payments=Count('executed_payments'),
        successful_payments=Count('executed_payments', filter=Q(executed_payments__status='success')),
        failed_payments=Count('executed_payments', filter=Q(executed_payments__status='failed')),
        total_amount_paid=Sum('executed_payments__amount', filter=Q(executed_payments__status='success'))
    ).filter(total_payments__gt=0).order_by('-total_payments')
    
    from settings_manager.models import get_setting
    context = {
        'user_requisition_stats': user_requisition_stats,
        'user_approval_stats': user_approval_stats,
        'user_payment_stats': user_payment_stats,
        'days': days,
        # Reporting settings
        'report_export_formats': get_report_export_formats(),
        'report_retention_months': get_report_retention_months(),
        'report_email_recipients': get_report_email_recipients(),
    }
    return render(request, 'reports/user_activity_report.html', context)
