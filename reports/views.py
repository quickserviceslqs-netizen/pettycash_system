from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Count, Q, Avg, F, Min, Subquery, OuterRef, ExpressionWrapper, DurationField, Exists
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncMonth
from transactions.models import Requisition, ApprovalTrail
from treasury.models import Payment, TreasuryFund, LedgerEntry, PaymentExecution
from django.contrib.auth import get_user_model
from django.http import HttpResponse
import csv
from openpyxl import Workbook

User = get_user_model()


def is_admin_user(user):
    """Check if user has admin role"""
    return user.role in ['Admin', 'Super Admin']


@login_required
@user_passes_test(is_admin_user)
def reports_dashboard(request):
    """
    Main reports dashboard with overview metrics and quick access to detailed reports.
    Shows key statistics across transactions, treasury, and approvals.
    """
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
    funds_below_reorder = TreasuryFund.objects.filter(current_balance__lt=F('reorder_level')).count()
    
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
    }
    
    return render(request, 'reports/dashboard.html', context)


@login_required
@user_passes_test(is_admin_user)
def transaction_report(request):
    """
    Detailed transaction/requisition report with filters and export capability.
    """
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

    # Pagination
    from django.core.paginator import Paginator
    try:
        page_size = int(request.GET.get('page_size', 25))
    except (TypeError, ValueError):
        page_size = 25
    page_size = max(5, min(page_size, 200))
    page_number = request.GET.get('page', 1)
    paginator = Paginator(requisitions, page_size)
    page_obj = paginator.get_page(page_number)
    
    # Get unique branches and departments for filters
    from organization.models import Branch, Department
    branches = Branch.objects.all().order_by('name')
    departments = Department.objects.all().order_by('name')
    
    context = {
        'requisitions': page_obj,
        'total_count': total_count,
        'total_amount': total_amount,
        'avg_amount': avg_amount,
        'days': days,
        'page_obj': page_obj,
        'page_size': page_size,
        'selected_status': status,
        'selected_branch': branch_id,
        'selected_department': department_id,
        'min_amount': min_amount,
        'max_amount': max_amount,
        'branches': branches,
        'departments': departments,
        'status_choices': Requisition.STATUS_CHOICES,
    }
    
    return render(request, 'reports/transaction_report.html', context)


@login_required
@user_passes_test(is_admin_user)
def transaction_report_export_csv(request):
    """Server-side CSV export for Transaction Report honoring filters."""
    # Filters (same as transaction_report)
    days = int(request.GET.get('days', 30))
    status = request.GET.get('status', '')
    branch_id = request.GET.get('branch', '')
    department_id = request.GET.get('department', '')
    min_amount = request.GET.get('min_amount', '')
    max_amount = request.GET.get('max_amount', '')

    start_date = timezone.now() - timedelta(days=days)
    qs = Requisition.objects.filter(created_at__gte=start_date).select_related(
        'requested_by', 'branch', 'department', 'cost_center'
    ).order_by('-created_at')

    if status:
        qs = qs.filter(status=status)
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    if department_id:
        qs = qs.filter(department_id=department_id)
    if min_amount:
        qs = qs.filter(amount__gte=min_amount)
    if max_amount:
        qs = qs.filter(amount__lte=max_amount)

    # Build CSV
    response = HttpResponse(content_type='text/csv')
    filename = f"transaction_report_{timezone.now().date()}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(['Transaction ID', 'Requested By', 'Branch', 'Department', 'Amount', 'Status', 'Created', 'Purpose'])
    for r in qs.iterator():
        writer.writerow([
            r.transaction_id,
            getattr(r.requested_by, 'username', ''),
            getattr(r.branch, 'name', '') if r.branch else '',
            getattr(r.department, 'name', '') if r.department else '',
            f"{r.amount}",
            r.get_status_display(),
            r.created_at.strftime('%Y-%m-%d %H:%M'),
            (r.purpose or '').replace('\n', ' ').strip(),
        ])
    return response


@login_required
@user_passes_test(is_admin_user)
def transaction_report_export_xlsx(request):
    """Server-side Excel export for Transaction Report honoring filters."""
    # Filters (same as transaction_report)
    days = int(request.GET.get('days', 30))
    status = request.GET.get('status', '')
    branch_id = request.GET.get('branch', '')
    department_id = request.GET.get('department', '')
    min_amount = request.GET.get('min_amount', '')
    max_amount = request.GET.get('max_amount', '')

    start_date = timezone.now() - timedelta(days=days)
    qs = Requisition.objects.filter(created_at__gte=start_date).select_related(
        'requested_by', 'branch', 'department', 'cost_center'
    ).order_by('-created_at')

    if status:
        qs = qs.filter(status=status)
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    if department_id:
        qs = qs.filter(department_id=department_id)
    if min_amount:
        qs = qs.filter(amount__gte=min_amount)
    if max_amount:
        qs = qs.filter(amount__lte=max_amount)

    wb = Workbook()
    ws = wb.active
    ws.title = 'Transactions'
    ws.append(['Transaction ID', 'Requested By', 'Branch', 'Department', 'Amount', 'Status', 'Created', 'Purpose'])
    for r in qs.iterator():
        ws.append([
            r.transaction_id,
            getattr(r.requested_by, 'username', ''),
            getattr(r.branch, 'name', '') if r.branch else '',
            getattr(r.department, 'name', '') if r.department else '',
            float(r.amount),
            r.get_status_display(),
            r.created_at.strftime('%Y-%m-%d %H:%M'),
            (r.purpose or '').replace('\n', ' ').strip(),
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"transaction_report_{timezone.now().date()}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


@login_required
@user_passes_test(is_admin_user)
def treasury_report(request):
    """
    Treasury fund balances and payment activity report.
    """
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
    
    context = {
        'funds': funds,
        'total_balance': total_balance,
        'funds_needing_replenishment': funds_needing_replenishment,
        'payment_stats': payment_stats,
        'status_stats': status_stats,
        'days': days,
    }
    
    return render(request, 'reports/treasury_report.html', context)


@login_required
@user_passes_test(is_admin_user)
def treasury_fund_detail(request, fund_id):
    """Drilldown: show ledger movements and executed payments for a fund."""
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)

    fund = TreasuryFund.objects.select_related('company', 'region', 'branch', 'department').get(fund_id=fund_id)

    # Ledger entries for this fund in date range
    ledger_qs = LedgerEntry.objects.filter(treasury_fund=fund, created_at__gte=start_date).select_related('payment_execution').order_by('-created_at')

    # Payments associated via payment execution -> ledger entry
    payments_qs = Payment.objects.filter(execution__ledger_entries__treasury_fund=fund, created_at__gte=start_date).select_related('requisition', 'executor', 'created_by').distinct().order_by('-created_at')

    # Pagination for ledger
    from django.core.paginator import Paginator
    try:
        ledger_page_size = int(request.GET.get('ledger_page_size', 25))
    except (TypeError, ValueError):
        ledger_page_size = 25
    ledger_page_size = max(5, min(ledger_page_size, 200))
    ledger_page = request.GET.get('ledger_page', 1)
    ledger_paginator = Paginator(ledger_qs, ledger_page_size)
    ledger_page_obj = ledger_paginator.get_page(ledger_page)

    # Pagination for payments
    try:
        pay_page_size = int(request.GET.get('pay_page_size', 25))
    except (TypeError, ValueError):
        pay_page_size = 25
    pay_page_size = max(5, min(pay_page_size, 200))
    pay_page = request.GET.get('pay_page', 1)
    pay_paginator = Paginator(payments_qs, pay_page_size)
    pay_page_obj = pay_paginator.get_page(pay_page)

    # Totals
    debits = ledger_qs.filter(entry_type='debit').aggregate(total=Sum('amount'))['total'] or 0
    credits = ledger_qs.filter(entry_type='credit').aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'fund': fund,
        'days': days,
        'ledger_page_obj': ledger_page_obj,
        'ledger_page_size': ledger_page_size,
        'pay_page_obj': pay_page_obj,
        'pay_page_size': pay_page_size,
        'debits': debits,
        'credits': credits,
    }
    return render(request, 'reports/treasury_fund_detail.html', context)


@login_required
@user_passes_test(is_admin_user)
def treasury_fund_ledger_export_csv(request, fund_id):
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    fund = TreasuryFund.objects.get(fund_id=fund_id)
    qs = LedgerEntry.objects.filter(treasury_fund=fund, created_at__gte=start_date).select_related('payment_execution').order_by('-created_at')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="fund_ledger_{fund_id}_{timezone.now().date()}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Timestamp', 'Type', 'Amount', 'Description', 'Payment Ref'])
    for e in qs.iterator():
        writer.writerow([
            e.created_at.strftime('%Y-%m-%d %H:%M'), e.entry_type, f"{e.amount}", (e.description or '').replace('\n', ' ').strip(), getattr(e.payment_execution, 'gateway_reference', '')
        ])
    return response


@login_required
@user_passes_test(is_admin_user)
def treasury_fund_ledger_export_xlsx(request, fund_id):
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    fund = TreasuryFund.objects.get(fund_id=fund_id)
    qs = LedgerEntry.objects.filter(treasury_fund=fund, created_at__gte=start_date).select_related('payment_execution').order_by('-created_at')
    wb = Workbook()
    ws = wb.active
    ws.title = 'Fund Ledger'
    ws.append(['Timestamp', 'Type', 'Amount', 'Description', 'Payment Ref'])
    for e in qs.iterator():
        ws.append([
            e.created_at.strftime('%Y-%m-%d %H:%M'), e.entry_type, float(e.amount), (e.description or '').replace('\n', ' ').strip(), getattr(e.payment_execution, 'gateway_reference', ''),
        ])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="fund_ledger_{fund_id}_{timezone.now().date()}.xlsx"'
    wb.save(response)
    return response


@login_required
@user_passes_test(is_admin_user)
def treasury_fund_payments_export_csv(request, fund_id):
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    fund = TreasuryFund.objects.get(fund_id=fund_id)
    qs = Payment.objects.filter(execution__ledger_entries__treasury_fund=fund, created_at__gte=start_date).select_related('requisition', 'executor', 'created_by').distinct().order_by('-created_at')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="fund_payments_{fund_id}_{timezone.now().date()}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Created', 'Payment ID', 'Amount', 'Method', 'Status', 'Destination', 'Requisition', 'Executor'])
    for p in qs.iterator():
        writer.writerow([
            p.created_at.strftime('%Y-%m-%d %H:%M'), p.payment_id, f"{p.amount}", p.method, p.status, (p.destination or ''), getattr(p.requisition, 'transaction_id', ''), getattr(p.executor, 'username', ''),
        ])
    return response


@login_required
@user_passes_test(is_admin_user)
def treasury_fund_payments_export_xlsx(request, fund_id):
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    fund = TreasuryFund.objects.get(fund_id=fund_id)
    qs = Payment.objects.filter(execution__ledger_entries__treasury_fund=fund, created_at__gte=start_date).select_related('requisition', 'executor', 'created_by').distinct().order_by('-created_at')
    wb = Workbook()
    ws = wb.active
    ws.title = 'Fund Payments'
    ws.append(['Created', 'Payment ID', 'Amount', 'Method', 'Status', 'Destination', 'Requisition', 'Executor'])
    for p in qs.iterator():
        ws.append([
            p.created_at.strftime('%Y-%m-%d %H:%M'), str(p.payment_id), float(p.amount), p.method, p.status, (p.destination or ''), getattr(p.requisition, 'transaction_id', ''), getattr(p.executor, 'username', ''),
        ])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="fund_payments_{fund_id}_{timezone.now().date()}.xlsx"'
    wb.save(response)
    return response


@login_required
@user_passes_test(is_admin_user)
def approval_report(request):
    """
    Approval workflow analytics: approval times, bottlenecks, approver performance.
    """
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
    
    # SLA: average time to first approval (hours)
    first_approved_subq = ApprovalTrail.objects.filter(
        requisition_id=OuterRef('pk'), action='approved'
    ).order_by().values('requisition_id').annotate(first_at=Min('timestamp')).values('first_at')[:1]
    req_with_first = Requisition.objects.filter(created_at__gte=start_date).annotate(
        first_approved_at=Subquery(first_approved_subq)
    ).filter(first_approved_at__isnull=False).annotate(
        time_to_first=ExpressionWrapper(F('first_approved_at') - F('created_at'), output_field=DurationField())
    )
    avg_time_to_first = req_with_first.aggregate(avg=Avg('time_to_first'))['avg']
    avg_time_to_first_hours = None
    if avg_time_to_first:
        avg_time_to_first_hours = round(avg_time_to_first.total_seconds() / 3600, 2)

    # Pagination for approval logs
    from django.core.paginator import Paginator
    try:
        page_size = int(request.GET.get('page_size', 25))
    except (TypeError, ValueError):
        page_size = 25
    page_size = max(5, min(page_size, 200))
    page_number = request.GET.get('page', 1)
    paginator = Paginator(approval_trails, page_size)
    approval_logs_page = paginator.get_page(page_number)
    
    # Average approval time (time from creation to first approval)
    requisitions_with_approvals = Requisition.objects.filter(
        created_at__gte=start_date,
        status__in=['paid', 'reviewed']
    ).select_related('requested_by')
    
    context = {
        'approval_logs': approval_logs_page,
        'approver_stats': approver_stats,
        'action_breakdown': action_breakdown,
        'days': days,
        'total_logs': approval_trails.count(),
        'page_obj': approval_logs_page,
        'page_size': page_size,
        'avg_time_to_first_hours': avg_time_to_first_hours,
    }
    
    return render(request, 'reports/approval_report.html', context)


@login_required
@user_passes_test(is_admin_user)
def approval_logs_export_csv(request):
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    qs = ApprovalTrail.objects.filter(timestamp__gte=start_date).select_related('user', 'requisition').order_by('-timestamp')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="approval_logs_{timezone.now().date()}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Timestamp', 'User', 'Action', 'Requisition', 'Comment'])
    for a in qs.iterator():
        writer.writerow([
            a.timestamp.strftime('%Y-%m-%d %H:%M'),
            getattr(a.user, 'username', ''),
            a.action,
            a.requisition_id,
            (a.comment or '').replace('\n', ' ').strip(),
        ])
    return response


@login_required
@user_passes_test(is_admin_user)
def approval_logs_export_xlsx(request):
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    qs = ApprovalTrail.objects.filter(timestamp__gte=start_date).select_related('user', 'requisition').order_by('-timestamp')

    wb = Workbook()
    ws = wb.active
    ws.title = 'Approval Logs'
    ws.append(['Timestamp', 'User', 'Action', 'Requisition', 'Comment'])
    for a in qs.iterator():
        ws.append([
            a.timestamp.strftime('%Y-%m-%d %H:%M'),
            getattr(a.user, 'username', ''),
            a.action,
            a.requisition_id,
            (a.comment or '').replace('\n', ' ').strip(),
        ])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="approval_logs_{timezone.now().date()}.xlsx"'
    wb.save(response)
    return response


@login_required
@user_passes_test(is_admin_user)
def approver_perf_export_csv(request):
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    approval_trails = ApprovalTrail.objects.filter(timestamp__gte=start_date)
    approver_stats = approval_trails.values('user__username', 'user__id').annotate(
        total_actions=Count('id'),
        approvals=Count('id', filter=Q(action='approved')),
        rejections=Count('id', filter=Q(action='rejected')),
        change_requests=Count('id', filter=Q(action='changes_requested'))
    ).order_by('-total_actions')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="approver_performance_{timezone.now().date()}.csv"'
    writer = csv.writer(response)
    writer.writerow(['User', 'User ID', 'Total Actions', 'Approvals', 'Rejections', 'Change Requests', 'Approval Rate %'])
    for s in approver_stats:
        rate = round((s['approvals'] / s['total_actions'] * 100.0), 2) if s['total_actions'] else 0
        writer.writerow([
            s['user__username'], s['user__id'], s['total_actions'], s['approvals'], s['rejections'], s['change_requests'], rate
        ])
    return response


@login_required
@user_passes_test(is_admin_user)
def approver_perf_export_xlsx(request):
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    approval_trails = ApprovalTrail.objects.filter(timestamp__gte=start_date)
    approver_stats = approval_trails.values('user__username', 'user__id').annotate(
        total_actions=Count('id'),
        approvals=Count('id', filter=Q(action='approved')),
        rejections=Count('id', filter=Q(action='rejected')),
        change_requests=Count('id', filter=Q(action='changes_requested'))
    ).order_by('-total_actions')

    wb = Workbook()
    ws = wb.active
    ws.title = 'Approver Performance'
    ws.append(['User', 'User ID', 'Total Actions', 'Approvals', 'Rejections', 'Change Requests', 'Approval Rate %'])
    for s in approver_stats:
        rate = round((s['approvals'] / s['total_actions'] * 100.0), 2) if s['total_actions'] else 0
        ws.append([
            s['user__username'], s['user__id'], s['total_actions'], s['approvals'], s['rejections'], s['change_requests'], rate
        ])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="approver_performance_{timezone.now().date()}.xlsx"'
    wb.save(response)
    return response


@login_required
@user_passes_test(is_admin_user)
def user_activity_report(request):
    """
    User activity report: requisition creation, approval actions, payment execution.
    """
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
    
    context = {
        'user_requisition_stats': user_requisition_stats,
        'user_approval_stats': user_approval_stats,
        'user_payment_stats': user_payment_stats,
        'days': days,
    }
    
    return render(request, 'reports/user_activity_report.html', context)


@login_required
@user_passes_test(is_admin_user)
def budget_vs_actuals_report(request):
    """Budget vs Actuals by Cost Center (monthly), with variance."""
    from reports.models import BudgetAllocation
    from organization.models import CostCenter, Department, Branch

    try:
        year = int(request.GET.get('year', timezone.now().year))
    except (TypeError, ValueError):
        year = timezone.now().year
    group = request.GET.get('group', 'cost_center')  # cost_center | department | branch

    # Actuals (sum of amounts) in the given year by month and scope
    reqs = Requisition.objects.filter(created_at__year=year).select_related('cost_center', 'department', 'branch')

    if group == 'department':
        actuals = reqs.annotate(month=TruncMonth('created_at')).values('month', 'department_id', 'department__name').annotate(actual=Sum('amount')).order_by('month', 'department__name')
    elif group == 'branch':
        actuals = reqs.annotate(month=TruncMonth('created_at')).values('month', 'branch_id', 'branch__name').annotate(actual=Sum('amount')).order_by('month', 'branch__name')
    else:
        actuals = reqs.annotate(month=TruncMonth('created_at')).values('month', 'cost_center_id', 'cost_center__name', 'department__name', 'branch__name').annotate(actual=Sum('amount')).order_by('month', 'cost_center__name')

    # Collect keys for budget lookup
    months = set()
    rows = []
    for a in actuals:
        month_num = a['month'].month if a['month'] else None
        months.add(month_num)
        rows.append(a)

    # Fetch budgets for the same scope
    budgets_qs = BudgetAllocation.objects.filter(year=year)
    budget_map = {}
    for b in budgets_qs.iterator():
        key = (
            'branch', b.branch_id
        ) if group == 'branch' else (
            ('department', b.department_id) if group == 'department' else ('cost_center', b.cost_center_id)
        )
        month_key = b.month or 0
        budget_map.setdefault((key[0], key[1], month_key), 0)
        budget_map[(key[0], key[1], month_key)] += float(b.amount)

    # Build result with variance
    data = []
    for r in rows:
        if group == 'branch':
            scope_key = ('branch', r.get('branch_id'))
            scope_name = r.get('branch__name') or '-'
        elif group == 'department':
            scope_key = ('department', r.get('department_id'))
            scope_name = r.get('department__name') or '-'
        else:
            scope_key = ('cost_center', r.get('cost_center_id'))
            scope_name = r.get('cost_center__name') or '-'

        month_num = r['month'].month if r['month'] else 0
        budget = budget_map.get((scope_key[0], scope_key[1], month_num), budget_map.get((scope_key[0], scope_key[1], 0), 0))
        actual = float(r['actual'] or 0)
        variance = actual - budget
        variance_pct = (variance / budget * 100.0) if budget else None
        data.append({
            'scope_name': scope_name,
            'month': r['month'],
            'actual': actual,
            'budget': budget,
            'variance': variance,
            'variance_pct': variance_pct,
        })

    # Sort by scope then month
    data.sort(key=lambda x: (x['scope_name'] or '', x['month']))

    context = {
        'year': year,
        'group': group,
        'rows': data,
    }
    return render(request, 'reports/budget_vs_actuals.html', context)


@login_required
@user_passes_test(is_admin_user)
def budget_vs_actuals_export_csv(request):
    year = int(request.GET.get('year', timezone.now().year))
    request.GET._mutable = True  # safe in view scope
    request.GET['group'] = request.GET.get('group', 'cost_center')
    response = budget_vs_actuals_report(request)
    # Re-run logic more directly for CSV to avoid template
    group = request.GET['group']
    from reports.models import BudgetAllocation
    reqs = Requisition.objects.filter(created_at__year=year).select_related('cost_center', 'department', 'branch')
    if group == 'department':
        actuals = reqs.annotate(month=TruncMonth('created_at')).values('month', 'department_id', 'department__name').annotate(actual=Sum('amount'))
    elif group == 'branch':
        actuals = reqs.annotate(month=TruncMonth('created_at')).values('month', 'branch_id', 'branch__name').annotate(actual=Sum('amount'))
    else:
        actuals = reqs.annotate(month=TruncMonth('created_at')).values('month', 'cost_center_id', 'cost_center__name').annotate(actual=Sum('amount'))
    budgets_qs = BudgetAllocation.objects.filter(year=year)
    budget_map = {}
    for b in budgets_qs.iterator():
        key = ('branch', b.branch_id) if group == 'branch' else (('department', b.department_id) if group == 'department' else ('cost_center', b.cost_center_id))
        month_key = b.month or 0
        budget_map.setdefault((key[0], key[1], month_key), 0)
        budget_map[(key[0], key[1], month_key)] += float(b.amount)
    # Build CSV
    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = f'attachment; filename="budget_vs_actuals_{year}.csv"'
    writer = csv.writer(resp)
    writer.writerow(['Scope', 'Month', 'Actual', 'Budget', 'Variance', 'Variance %'])
    for r in actuals:
        scope_name = r.get('branch__name') or r.get('department__name') or r.get('cost_center__name') or '-'
        month_num = r['month'].month if r['month'] else 0
        budget = budget_map.get(('branch', r.get('branch_id'), month_num), 0) if group == 'branch' else (
            budget_map.get(('department', r.get('department_id'), month_num), 0) if group == 'department' else budget_map.get(('cost_center', r.get('cost_center_id'), month_num), 0)
        )
        actual = float(r['actual'] or 0)
        variance = actual - budget
        variance_pct = round((variance / budget * 100.0), 2) if budget else None
        writer.writerow([scope_name, month_num, actual, budget, variance, variance_pct if variance_pct is not None else ''])
    return resp


@login_required
@user_passes_test(is_admin_user)
def budget_vs_actuals_export_xlsx(request):
    year = int(request.GET.get('year', timezone.now().year))
    group = request.GET.get('group', 'cost_center')
    from reports.models import BudgetAllocation
    reqs = Requisition.objects.filter(created_at__year=year).select_related('cost_center', 'department', 'branch')
    if group == 'department':
        actuals = reqs.annotate(month=TruncMonth('created_at')).values('month', 'department_id', 'department__name').annotate(actual=Sum('amount'))
    elif group == 'branch':
        actuals = reqs.annotate(month=TruncMonth('created_at')).values('month', 'branch_id', 'branch__name').annotate(actual=Sum('amount'))
    else:
        actuals = reqs.annotate(month=TruncMonth('created_at')).values('month', 'cost_center_id', 'cost_center__name').annotate(actual=Sum('amount'))
    budgets_qs = BudgetAllocation.objects.filter(year=year)
    budget_map = {}
    for b in budgets_qs.iterator():
        key = ('branch', b.branch_id) if group == 'branch' else (('department', b.department_id) if group == 'department' else ('cost_center', b.cost_center_id))
        month_key = b.month or 0
        budget_map.setdefault((key[0], key[1], month_key), 0)
        budget_map[(key[0], key[1], month_key)] += float(b.amount)
    wb = Workbook()
    ws = wb.active
    ws.title = 'Budget vs Actuals'
    ws.append(['Scope', 'Month', 'Actual', 'Budget', 'Variance', 'Variance %'])
    for r in actuals:
        scope_name = r.get('branch__name') or r.get('department__name') or r.get('cost_center__name') or '-'
        month_num = r['month'].month if r['month'] else 0
        budget = budget_map.get(('branch', r.get('branch_id'), month_num), 0) if group == 'branch' else (
            budget_map.get(('department', r.get('department_id'), month_num), 0) if group == 'department' else budget_map.get(('cost_center', r.get('cost_center_id'), month_num), 0)
        )
        actual = float(r['actual'] or 0)
        variance = actual - budget
        variance_pct = round((variance / budget * 100.0), 2) if budget else None
        ws.append([scope_name, month_num, actual, budget, variance, variance_pct if variance_pct is not None else ''])
    resp = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = f'attachment; filename="budget_vs_actuals_{year}.xlsx"'
    wb.save(resp)
    return resp


@login_required
@user_passes_test(is_admin_user)
def stuck_approvals_report(request):
    """List requisitions stuck in pending statuses beyond a threshold number of days."""
    older_than = int(request.GET.get('older_than', 7))
    status_filter = request.GET.get('status', 'pending_only')  # 'pending_only' or 'all_pending_*'
    start_cutoff = timezone.now() - timedelta(days=older_than)

    qs = Requisition.objects.filter(created_at__lt=start_cutoff).select_related(
        'requested_by', 'branch', 'department'
    )
    if status_filter == 'pending_only':
        qs = qs.filter(status__startswith='pending')
    else:
        qs = qs.filter(status__in=[s for s, _ in Requisition.STATUS_CHOICES if s.startswith('pending')])

    qs = qs.order_by('created_at')

    # Aggregates by status
    by_status = qs.values('status').annotate(count=Count('transaction_id')).order_by('-count')

    # Helper to compute age in days
    def age_days(dt):
        return (timezone.now() - dt).days

    items = [
        {
            'transaction_id': r.transaction_id,
            'requested_by': getattr(r.requested_by, 'username', ''),
            'branch': getattr(r.branch, 'name', None),
            'department': getattr(r.department, 'name', None),
            'amount': r.amount,
            'status': r.status,
            'created_at': r.created_at,
            'age_days': age_days(r.created_at),
            'next_approver': getattr(r.next_approver, 'username', None),
        }
        for r in qs
    ]

    context = {
        'older_than': older_than,
        'status_filter': status_filter,
        'by_status': by_status,
        'items': items,
        'total': len(items),
    }
    return render(request, 'reports/stuck_approvals.html', context)


@login_required
@user_passes_test(is_admin_user)
def threshold_overrides_report(request):
    """Requisitions that exceeded or bypassed configured approval thresholds."""
    days = int(request.GET.get('days', 90))
    start_date = timezone.now() - timedelta(days=days)

    # Subquery: requisitions with any override/skipped roles in approval trail
    trail_overrides_qs = ApprovalTrail.objects.filter(
        requisition_id=OuterRef('pk')
    ).filter(
        Q(override=True) | Q(skipped_roles__isnull=False)
    )

    # Build base filter for out-of-range amounts relative to applied threshold
    out_of_range_q = (
        Q(applied_threshold__isnull=False) & (
            Q(amount__lt=F('applied_threshold__min_amount')) |
            Q(amount__gt=F('applied_threshold__max_amount'))
        )
    )

    qs = Requisition.objects.filter(created_at__gte=start_date).select_related(
        'requested_by', 'branch', 'department', 'applied_threshold'
    ).annotate(
        has_trail_override=Exists(trail_overrides_qs)
    ).filter(
        out_of_range_q | Q(is_fast_tracked=True) | Q(pk__in=Subquery(
            ApprovalTrail.objects.filter(Q(override=True) | Q(skipped_roles__isnull=False))
            .values('requisition_id')
        ))
    ).order_by('-created_at')

    # Categorize
    by_category = {
        'out_of_range': qs.filter(out_of_range_q).count(),
        'fast_tracked': qs.filter(is_fast_tracked=True).count(),
        'trail_override': qs.filter(has_trail_override=True).count(),
    }

    items = [
        {
            'transaction_id': r.transaction_id,
            'requested_by': getattr(r.requested_by, 'username', ''),
            'branch': getattr(r.branch, 'name', None),
            'department': getattr(r.department, 'name', None),
            'amount': r.amount,
            'status': r.status,
            'created_at': r.created_at,
            'applied_threshold': getattr(r.applied_threshold, 'name', None),
            'min_amount': getattr(r.applied_threshold, 'min_amount', None),
            'max_amount': getattr(r.applied_threshold, 'max_amount', None),
            'is_fast_tracked': r.is_fast_tracked,
            'has_trail_override': r.has_trail_override,
        }
        for r in qs
    ]

    context = {
        'days': days,
        'items': items,
        'total': len(items),
        'by_category': by_category,
    }
    return render(request, 'reports/threshold_overrides.html', context)


@login_required
@user_passes_test(is_admin_user)
def threshold_overrides_export_csv(request):
    days = int(request.GET.get('days', 90))
    start_date = timezone.now() - timedelta(days=days)
    out_of_range_q = (
        Q(applied_threshold__isnull=False) & (
            Q(amount__lt=F('applied_threshold__min_amount')) |
            Q(amount__gt=F('applied_threshold__max_amount'))
        )
    )
    ovr_ids = ApprovalTrail.objects.filter(Q(override=True) | Q(skipped_roles__isnull=False)).values('requisition_id')
    qs = Requisition.objects.filter(created_at__gte=start_date).select_related(
        'requested_by', 'branch', 'department', 'applied_threshold'
    ).filter(
        out_of_range_q | Q(is_fast_tracked=True) | Q(pk__in=Subquery(ovr_ids))
    ).order_by('-created_at')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="threshold_overrides_{timezone.now().date()}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Transaction ID', 'Requested By', 'Branch', 'Department', 'Amount', 'Status', 'Created', 'Applied Threshold', 'Min', 'Max', 'Fast Tracked', 'Trail Override'])
    for r in qs.iterator():
        writer.writerow([
            r.transaction_id,
            getattr(r.requested_by, 'username', ''),
            getattr(r.branch, 'name', '') if r.branch else '',
            getattr(r.department, 'name', '') if r.department else '',
            f"{r.amount}",
            r.status,
            r.created_at.strftime('%Y-%m-%d %H:%M'),
            getattr(r.applied_threshold, 'name', ''),
            getattr(r.applied_threshold, 'min_amount', ''),
            getattr(r.applied_threshold, 'max_amount', ''),
            'Yes' if r.is_fast_tracked else 'No',
            'Yes' if ApprovalTrail.objects.filter(requisition_id=r.pk).filter(Q(override=True) | Q(skipped_roles__isnull=False)).exists() else 'No',
        ])
    return response
