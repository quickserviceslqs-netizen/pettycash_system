"""
Treasury Admin Views
User-friendly interface for managing treasury funds, payments, ledger, and variances
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.utils import timezone
from decimal import Decimal
from treasury.models import (
    TreasuryFund, Payment, PaymentExecution, LedgerEntry, 
    VarianceAdjustment
)
from organization.models import Company, Region, Branch
from transactions.models import Requisition


# ==================== TREASURY FUNDS ====================

@login_required
@permission_required('treasury.view_treasuryfund', raise_exception=True)
def manage_funds(request):
    """View and manage all treasury funds"""
    
    # Filters
    company_filter = request.GET.get('company', '')
    region_filter = request.GET.get('region', '')
    low_balance_only = request.GET.get('low_balance', '') == 'on'
    
    funds = TreasuryFund.objects.all().select_related('company', 'region', 'branch')
    
    if company_filter:
        funds = funds.filter(company_id=company_filter)
    
    if region_filter:
        funds = funds.filter(region_id=region_filter)
    
    if low_balance_only:
        funds = [f for f in funds if f.check_reorder_needed()]
    
    # Get stats
    total_balance = funds.aggregate(total=Sum('current_balance'))['total'] or Decimal('0.00')
    low_balance_count = sum(1 for f in funds if f.check_reorder_needed())
    
    companies = Company.objects.all()
    regions = Region.objects.all()
    
    context = {
        'funds': funds,
        'total_balance': total_balance,
        'low_balance_count': low_balance_count,
        'companies': companies,
        'regions': regions,
        'company_filter': company_filter,
        'region_filter': region_filter,
        'low_balance_only': low_balance_only,
    }
    
    return render(request, 'treasury/manage_funds.html', context)


@login_required
@permission_required('treasury.add_treasuryfund', raise_exception=True)
def create_fund(request):
    """Create a new treasury fund"""
    
    if request.method == 'POST':
        try:
            company_id = request.POST.get('company')
            region_id = request.POST.get('region') or None
            branch_id = request.POST.get('branch') or None
            current_balance = request.POST.get('current_balance') or '0.00'
            reorder_level = request.POST.get('reorder_level') or '50000.00'
            
            if not company_id:
                messages.error(request, 'Company is required.')
                return redirect('treasury:create_fund')
            
            # Check for existing fund
            existing = TreasuryFund.objects.filter(
                company_id=company_id,
                region_id=region_id,
                branch_id=branch_id
            ).exists()
            
            if existing:
                messages.error(request, 'A fund already exists for this location.')
                return redirect('treasury:create_fund')
            
            fund = TreasuryFund.objects.create(
                company_id=company_id,
                region_id=region_id,
                branch_id=branch_id,
                current_balance=Decimal(current_balance),
                reorder_level=Decimal(reorder_level),
            )
            
            messages.success(request, f'Treasury fund created successfully!')
            return redirect('treasury:manage_funds')
            
        except Exception as e:
            messages.error(request, f'Error creating fund: {str(e)}')
    
    companies = Company.objects.all()
    regions = Region.objects.all()
    branches = Branch.objects.all()
    
    context = {
        'companies': companies,
        'regions': regions,
        'branches': branches,
    }
    
    return render(request, 'treasury/create_fund.html', context)


@login_required
@permission_required('treasury.change_treasuryfund', raise_exception=True)
def edit_fund(request, fund_id):
    """Edit an existing treasury fund"""
    
    fund = get_object_or_404(TreasuryFund, fund_id=fund_id)
    
    if request.method == 'POST':
        try:
            fund.current_balance = Decimal(request.POST.get('current_balance', '0.00'))
            fund.reorder_level = Decimal(request.POST.get('reorder_level', '50000.00'))
            fund.save()
            
            messages.success(request, 'Fund updated successfully!')
            return redirect('treasury:manage_funds')
            
        except Exception as e:
            messages.error(request, f'Error updating fund: {str(e)}')
    
    context = {
        'fund': fund,
    }
    
    return render(request, 'treasury/edit_fund.html', context)


# ==================== PAYMENTS ====================

@login_required
@permission_required('treasury.view_payment', raise_exception=True)
def manage_payments(request):
    """View and manage all payments"""
    
    # Filters
    status_filter = request.GET.get('status', '')
    method_filter = request.GET.get('method', '')
    search_query = request.GET.get('search', '')
    
    payments = Payment.objects.all().select_related(
        'requisition', 'executor', 'requisition__requested_by'
    )
    
    if status_filter:
        payments = payments.filter(status=status_filter)
    
    if method_filter:
        payments = payments.filter(method=method_filter)
    
    if search_query:
        payments = payments.filter(
            Q(payment_id__icontains=search_query) |
            Q(destination__icontains=search_query) |
            Q(requisition__transaction_id__icontains=search_query)
        )
    
    payments = payments.order_by('-created_at')[:100]  # Limit to 100 recent
    
    # Stats
    stats = {
        'pending': Payment.objects.filter(status='pending').count(),
        'executing': Payment.objects.filter(status='executing').count(),
        'success': Payment.objects.filter(status='success').count(),
        'failed': Payment.objects.filter(status='failed').count(),
    }
    
    context = {
        'payments': payments,
        'stats': stats,
        'status_filter': status_filter,
        'method_filter': method_filter,
        'search_query': search_query,
        'status_choices': Payment.STATUS_CHOICES,
        'method_choices': Payment.PAYMENT_METHOD_CHOICES,
    }
    
    return render(request, 'treasury/manage_payments.html', context)


@login_required
@permission_required('treasury.add_payment', raise_exception=True)
def create_payment(request, requisition_id):
    """Create a payment for an approved requisition"""
    
    requisition = get_object_or_404(Requisition, transaction_id=requisition_id)
    
    # Verify requisition is approved
    if requisition.status != 'approved':
        messages.error(request, 'Only approved requisitions can have payments created.')
        return redirect('transactions:view_requisition', requisition_id=requisition_id)
    
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount'))
            method = request.POST.get('method')
            destination = request.POST.get('destination')
            otp_required = request.POST.get('otp_required') == 'on'
            
            if not all([amount, method, destination]):
                messages.error(request, 'All fields are required.')
                return redirect('treasury:create_payment', requisition_id=requisition_id)
            
            payment = Payment.objects.create(
                requisition=requisition,
                amount=amount,
                method=method,
                destination=destination,
                otp_required=otp_required,
                status='pending',
            )
            
            messages.success(request, f'Payment created successfully! Payment ID: {payment.payment_id}')
            return redirect('treasury:manage_payments')
            
        except Exception as e:
            messages.error(request, f'Error creating payment: {str(e)}')
    
    context = {
        'requisition': requisition,
        'method_choices': Payment.PAYMENT_METHOD_CHOICES,
    }
    
    return render(request, 'treasury/create_payment.html', context)


@login_required
@permission_required('treasury.change_payment', raise_exception=True)
def execute_payment(request, payment_id):
    """Execute a pending payment"""
    
    payment = get_object_or_404(Payment, payment_id=payment_id)
    
    # Check if user can execute
    if not payment.can_execute(request.user):
        messages.error(request, 'You do not have permission to execute this payment.')
        return redirect('treasury:manage_payments')
    
    if payment.status != 'pending':
        messages.error(request, f'Payment is already {payment.status}. Cannot execute.')
        return redirect('treasury:manage_payments')
    
    if request.method == 'POST':
        try:
            # Simplified execution (without actual gateway integration)
            gateway_reference = request.POST.get('gateway_reference') or f'SIM-{payment.payment_id.hex[:10].upper()}'
            
            # Mark payment as success
            payment.mark_success(request.user)
            
            # Create execution record
            execution = PaymentExecution.objects.create(
                payment=payment,
                executor=request.user,
                gateway_reference=gateway_reference,
                gateway_status='SUCCESS',
                otp_verified_at=timezone.now() if payment.otp_required else None,
                otp_verified_by=request.user if payment.otp_required else None,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
            )
            
            # Create ledger entry (debit from fund)
            # Find appropriate treasury fund
            req = payment.requisition
            treasury_fund = TreasuryFund.objects.filter(
                company=req.requested_by.company,
                branch=req.requested_by.branch,
            ).first()
            
            if treasury_fund:
                LedgerEntry.objects.create(
                    treasury_fund=treasury_fund,
                    payment_execution=execution,
                    entry_type='debit',
                    amount=payment.amount,
                    description=f'Payment for requisition {req.transaction_id}',
                )
                
                # Update fund balance
                treasury_fund.current_balance -= payment.amount
                treasury_fund.save()
            
            messages.success(request, f'Payment executed successfully! Reference: {gateway_reference}')
            return redirect('treasury:manage_payments')
            
        except Exception as e:
            payment.mark_failed(str(e))
            messages.error(request, f'Payment execution failed: {str(e)}')
    
    context = {
        'payment': payment,
        'requisition': payment.requisition,
    }
    
    return render(request, 'treasury/execute_payment.html', context)


# ==================== LEDGER ====================

@login_required
@permission_required('treasury.view_ledgerentry', raise_exception=True)
def view_ledger(request):
    """View ledger entries with filters"""
    
    # Filters
    fund_filter = request.GET.get('fund', '')
    entry_type_filter = request.GET.get('entry_type', '')
    reconciled_filter = request.GET.get('reconciled', '')
    
    entries = LedgerEntry.objects.all().select_related(
        'treasury_fund', 'payment_execution', 'reconciled_by'
    )
    
    if fund_filter:
        entries = entries.filter(treasury_fund_id=fund_filter)
    
    if entry_type_filter:
        entries = entries.filter(entry_type=entry_type_filter)
    
    if reconciled_filter == 'yes':
        entries = entries.filter(reconciled=True)
    elif reconciled_filter == 'no':
        entries = entries.filter(reconciled=False)
    
    entries = entries.order_by('-created_at')[:200]  # Limit to 200 recent
    
    funds = TreasuryFund.objects.all()
    
    # Stats
    total_debits = entries.filter(entry_type='debit').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    total_credits = entries.filter(entry_type='credit').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    unreconciled_count = entries.filter(reconciled=False).count()
    
    context = {
        'entries': entries,
        'funds': funds,
        'total_debits': total_debits,
        'total_credits': total_credits,
        'unreconciled_count': unreconciled_count,
        'fund_filter': fund_filter,
        'entry_type_filter': entry_type_filter,
        'reconciled_filter': reconciled_filter,
        'entry_type_choices': LedgerEntry.ENTRY_TYPE_CHOICES,
    }
    
    return render(request, 'treasury/view_ledger.html', context)


# ==================== VARIANCE ADJUSTMENTS ====================

@login_required
@permission_required('treasury.view_varianceadjustment', raise_exception=True)
def manage_variances(request):
    """View all variance adjustments"""
    
    # Filters
    status_filter = request.GET.get('status', '')
    fund_filter = request.GET.get('fund', '')
    
    variances = VarianceAdjustment.objects.all().select_related(
        'treasury_fund', 'initiated_by', 'approved_by'
    )
    
    if status_filter:
        variances = variances.filter(status=status_filter)
    
    if fund_filter:
        variances = variances.filter(treasury_fund_id=fund_filter)
    
    variances = variances.order_by('-created_at')
    
    funds = TreasuryFund.objects.all()
    
    context = {
        'variances': variances,
        'funds': funds,
        'status_filter': status_filter,
        'fund_filter': fund_filter,
        'status_choices': VarianceAdjustment.STATUS_CHOICES,
    }
    
    return render(request, 'treasury/manage_variances.html', context)


@login_required
@permission_required('treasury.add_varianceadjustment', raise_exception=True)
def create_variance(request):
    """Create a variance adjustment"""
    
    if request.method == 'POST':
        try:
            fund_id = request.POST.get('fund')
            adjusted_amount = Decimal(request.POST.get('adjusted_amount'))
            reason = request.POST.get('reason')
            
            if not all([fund_id, reason]):
                messages.error(request, 'Fund and reason are required.')
                return redirect('treasury:create_variance')
            
            fund = TreasuryFund.objects.get(fund_id=fund_id)
            original_amount = fund.current_balance
            variance_amount = adjusted_amount - original_amount
            
            variance = VarianceAdjustment.objects.create(
                treasury_fund=fund,
                original_amount=original_amount,
                adjusted_amount=adjusted_amount,
                variance_amount=variance_amount,
                reason=reason,
                initiated_by=request.user,
                status='pending',
            )
            
            messages.success(request, f'Variance adjustment created. Pending CFO approval.')
            return redirect('treasury:manage_variances')
            
        except Exception as e:
            messages.error(request, f'Error creating variance: {str(e)}')
    
    funds = TreasuryFund.objects.all()
    
    context = {
        'funds': funds,
    }
    
    return render(request, 'treasury/create_variance.html', context)


@login_required
@permission_required('treasury.change_varianceadjustment', raise_exception=True)
def approve_variance(request, variance_id):
    """Approve or reject a variance adjustment (CFO only)"""
    
    # Only CFO or Admin can approve
    if request.user.role.lower() not in ['cfo', 'admin']:
        messages.error(request, 'Only CFO can approve variance adjustments.')
        return redirect('treasury:manage_variances')
    
    variance = get_object_or_404(VarianceAdjustment, adjustment_id=variance_id)
    
    if variance.status != 'pending':
        messages.error(request, f'Variance is already {variance.status}.')
        return redirect('treasury:manage_variances')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            variance.status = 'approved'
            variance.approved_by = request.user
            variance.approved_at = timezone.now()
            variance.save()
            
            # Apply adjustment to fund
            fund = variance.treasury_fund
            fund.current_balance = variance.adjusted_amount
            fund.save()
            
            # Create ledger entry
            LedgerEntry.objects.create(
                treasury_fund=fund,
                entry_type='adjustment',
                amount=abs(variance.variance_amount),
                description=f'Variance adjustment: {variance.reason}',
                reconciled=True,
                reconciled_by=request.user,
                reconciliation_timestamp=timezone.now(),
            )
            
            messages.success(request, 'Variance adjustment approved and applied.')
            
        elif action == 'reject':
            variance.status = 'rejected'
            variance.approved_by = request.user
            variance.approved_at = timezone.now()
            variance.save()
            
            messages.success(request, 'Variance adjustment rejected.')
        
        return redirect('treasury:manage_variances')
    
    context = {
        'variance': variance,
    }
    
    return render(request, 'treasury/approve_variance.html', context)
