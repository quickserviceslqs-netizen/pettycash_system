"""
Dashboard Service - Aggregates metrics for Treasury Dashboard.
Calculates real-time fund status, payment volume, alerts, and forecasts.
"""

from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncDate
from treasury.models import (
    TreasuryDashboard, TreasuryFund, Payment, Alert, LedgerEntry, 
    VarianceAdjustment, ReplenishmentRequest, FundForecast, DashboardMetric
)
from transactions.models import Requisition
from organization.models import Company


class DashboardService:
    """
    Service for calculating and caching dashboard metrics.
    Called on-demand and refreshed hourly via background job.
    """
    
    @staticmethod
    def calculate_dashboard_metrics(company_id, region_id=None, branch_id=None):
        """
        Calculate all dashboard metrics for a company/region/branch.
        Returns: TreasuryDashboard object with aggregated data.
        """
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return None
        
        # Get or create dashboard
        dashboard, created = TreasuryDashboard.objects.get_or_create(
            company=company,
            region_id=region_id,
            branch_id=branch_id,
            defaults={'calculated_at': timezone.now()}
        )
        
        # Filter funds by region/branch if specified
        funds_query = TreasuryFund.objects.filter(company=company)
        if region_id:
            funds_query = funds_query.filter(region_id=region_id)
        if branch_id:
            funds_query = funds_query.filter(branch_id=branch_id)
        
        # Calculate fund metrics
        funds = list(funds_query)
        dashboard.total_funds = len(funds)
        dashboard.total_balance = sum(f.current_balance for f in funds) if funds else Decimal('0.00')
        
        # Calculate utilization and fund status
        funds_below_reorder = 0
        funds_critical = 0
        for fund in funds:
            if fund.current_balance < fund.reorder_level:
                funds_below_reorder += 1
                if fund.current_balance < (fund.reorder_level * Decimal('0.8')):
                    funds_critical += 1
        
        dashboard.funds_below_reorder = funds_below_reorder
        dashboard.funds_critical = funds_critical
        
        # Calculate utilization percentage
        if funds:
            avg_utilization = sum(
                (f.current_balance / f.reorder_level * 100) if f.reorder_level > 0 else 0 
                for f in funds
            ) / len(funds)
            dashboard.total_utilization_pct = Decimal(str(min(avg_utilization, 100)))
        
        # Calculate payment metrics (today)
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # Today's payments (linked via requisition -> company/region/branch)
        payments_today_q = Payment.objects.filter(status='success', created_at__date=today)
        payments_today_q = payments_today_q.filter(requisition__company=company)
        if region_id:
            payments_today_q = payments_today_q.filter(requisition__region_id=region_id)
        if branch_id:
            payments_today_q = payments_today_q.filter(requisition__branch_id=branch_id)
        payments_today = payments_today_q
        dashboard.payments_today = payments_today.count()
        dashboard.total_amount_today = payments_today.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Week's payments
        payments_week_q = Payment.objects.filter(status='success', created_at__date__gte=week_start)
        payments_week_q = payments_week_q.filter(requisition__company=company)
        if region_id:
            payments_week_q = payments_week_q.filter(requisition__region_id=region_id)
        if branch_id:
            payments_week_q = payments_week_q.filter(requisition__branch_id=branch_id)
        payments_week = payments_week_q
        dashboard.payments_this_week = payments_week.count()
        dashboard.total_amount_this_week = payments_week.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Month's payments
        payments_month_q = Payment.objects.filter(status='success', created_at__date__gte=month_start)
        payments_month_q = payments_month_q.filter(requisition__company=company)
        if region_id:
            payments_month_q = payments_month_q.filter(requisition__region_id=region_id)
        if branch_id:
            payments_month_q = payments_month_q.filter(requisition__branch_id=branch_id)
        payments_month = payments_month_q
        dashboard.payments_this_month = payments_month.count()
        dashboard.total_amount_this_month = payments_month.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Calculate alert metrics
        unresolved_alerts = Alert.objects.filter(
            related_fund__in=funds_query,
            resolved_at__isnull=True
        )
        dashboard.active_alerts = unresolved_alerts.count()
        dashboard.critical_alerts = unresolved_alerts.filter(severity='Critical').count()
        
        # Calculate replenishment metrics
        pending_replenishments = ReplenishmentRequest.objects.filter(
            treasury_fund__in=funds_query,
            status__in=['pending', 'approved']
        )
        dashboard.pending_replenishments = pending_replenishments.count()
        dashboard.pending_replenishment_amount = pending_replenishments.aggregate(
            total=Sum('requested_amount')
        )['total'] or Decimal('0.00')
        
        # Calculate variance metrics
        pending_variances = VarianceAdjustment.objects.filter(
            treasury_fund__in=funds_query,
            status='pending'
        )
        dashboard.pending_variances = pending_variances.count()
        dashboard.pending_variance_amount = pending_variances.aggregate(
            total=Sum('variance_amount')
        )['total'] or Decimal('0.00')
        
        # Set timestamps
        # Set calculated_at for newly-created dashboards during get_or_create
        if created:
            dashboard.calculated_at = timezone.now()
        else:
            dashboard.calculated_at = timezone.now()
        dashboard.save()
        
        return dashboard
    
    @staticmethod
    def get_fund_status_cards(company_id, region_id=None, branch_id=None):
        """
        Get detailed status for each fund (for dashboard cards).
        """
        funds_query = TreasuryFund.objects.filter(company_id=company_id)
        if region_id:
            funds_query = funds_query.filter(region_id=region_id)
        if branch_id:
            funds_query = funds_query.filter(branch_id=branch_id)
        
        cards = []
        for fund in funds_query:
            # Determine status
            if fund.current_balance < fund.reorder_level:
                if fund.current_balance < (fund.reorder_level * Decimal('0.8')):
                    status = 'CRITICAL'
                else:
                    status = 'WARNING'
            else:
                status = 'OK'
            
            # Calculate utilization
            utilization_pct = (fund.current_balance / fund.reorder_level * 100) if fund.reorder_level > 0 else 0
            
            # Get transaction count
            transaction_count = LedgerEntry.objects.filter(
                treasury_fund=fund,
                created_at__date__gte=timezone.now().date()
            ).count()
            
            cards.append({
                'fund_id': str(fund.fund_id),
                'name': str(fund),
                'company': fund.company.name,
                'region': fund.region.name if fund.region else None,
                'branch': fund.branch.name if fund.branch else None,
                'current_balance': float(fund.current_balance),
                'reorder_level': float(fund.reorder_level),
                'status': status,
                'utilization_pct': float(utilization_pct),
                'last_replenished': fund.last_replenished,
                'transaction_count': transaction_count,
            })
        
        return cards
    
    @staticmethod
    def get_pending_payments(company_id, region_id=None, branch_id=None, limit=10):
        """
        Get pending payments ready for execution (API).
        """
        # Filter requisitions by company/region/branch scope
        requisitions = Requisition.objects.filter(company_id=company_id, status='pending')
        if region_id:
            requisitions = requisitions.filter(region_id=region_id)
        if branch_id:
            requisitions = requisitions.filter(branch_id=branch_id)
        
        payments = Payment.objects.filter(
            requisition__in=requisitions,
            status='pending'
        ).select_related('requisition', 'executor')[:limit]
        
        return list(payments)
    
    @staticmethod
    def get_recent_payments(company_id, region_id=None, branch_id=None, limit=10):
        """
        Get recent executed payments with status.
        """
        # Filter requisitions by company/region/branch scope
        requisitions = Requisition.objects.filter(company_id=company_id)
        if region_id:
            requisitions = requisitions.filter(region_id=region_id)
        if branch_id:
            requisitions = requisitions.filter(branch_id=branch_id)
        
        payments = Payment.objects.filter(
            requisition__in=requisitions,
            status__in=['success', 'failed']
        ).select_related('requisition').order_by('-updated_at')[:limit]
        
        return list(payments)
    
    @staticmethod
    def record_metric(dashboard, metric_type, value):
        """
        Record a historical metric for trend analysis.
        """
        today = timezone.now().date()
        now_hour = timezone.now().hour
        
        metric, created = DashboardMetric.objects.get_or_create(
            dashboard=dashboard,
            metric_type=metric_type,
            metric_date=today,
            metric_hour=now_hour,
            defaults={'value': value}
        )
        
        if not created:
            metric.value = value
            metric.save(update_fields=['value'])
        
        return metric
    
    @staticmethod
    def refresh_dashboard_cache():
        """
        Refresh all dashboards (call hourly via background job).
        """
        companies = Company.objects.all()
        refreshed_count = 0
        
        for company in companies:
            dashboard = DashboardService.calculate_dashboard_metrics(company.id)
            if dashboard:
                refreshed_count += 1
        
        return refreshed_count
