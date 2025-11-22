"""
Treasury payment execution views and API endpoints (Phase 5).

Endpoints:
- POST /payments/{payment_id}/execute/ - Execute payment
- POST /payments/{payment_id}/verify-otp/ - Verify OTP
- POST /payments/{payment_id}/send-otp/ - Send OTP
- GET /payments/{payment_id}/ - Get payment status
- GET /treasury-funds/{fund_id}/balance/ - Get current balance
- POST /treasury-funds/{fund_id}/replenish/ - Manual replenishment (admin only)
- PATCH /variance-adjustments/{variance_id}/approve/ - Approve variance (CFO only)
- POST /api/mpesa/callback/ - M-Pesa STK Push callback
"""

from rest_framework import viewsets, serializers, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.http import JsonResponse
import json

from treasury.models import (
    Payment, PaymentExecution, TreasuryFund, 
    LedgerEntry, VarianceAdjustment, ReplenishmentRequest
)
from treasury.services.payment_service import (
    PaymentExecutionService, ReconciliationService, OTPService
)
from treasury.services.mpesa_service import process_mpesa_callback
from treasury.permissions import DjangoModelPermissionsWithView, RequireAppAccess


# ============================================================================
# Serializers
# ============================================================================

class TreasuryFundSerializer(serializers.ModelSerializer):
    class Meta:
        model = TreasuryFund
        fields = ['fund_id', 'company', 'region', 'branch', 'current_balance', 'reorder_level', 'last_replenished']
        read_only_fields = ['current_balance', 'last_replenished']


class PaymentExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentExecution
        fields = ['execution_id', 'executor', 'gateway_reference', 'gateway_status', 
                  'otp_verified_at', 'ip_address', 'created_at']
        read_only_fields = fields


class PaymentSerializer(serializers.ModelSerializer):
    payment_execution = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = ['payment_id', 'requisition', 'amount', 'method', 'destination', 
                  'status', 'executor', 'execution_timestamp', 'otp_required', 
                  'otp_verified', 'retry_count', 'last_error', 'payment_execution', 
                  'created_at']
        read_only_fields = ['payment_id', 'status', 'executor', 'execution_timestamp', 
                           'otp_verified', 'retry_count', 'last_error', 'created_at']
    
    def get_payment_execution(self, obj):
        execution = PaymentExecution.objects.filter(payment=obj).first()
        if execution:
            return PaymentExecutionSerializer(execution).data
        return None


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = ['ledger_id', 'fund', 'entry_type', 'amount', 'description', 
                  'reconciled', 'created_at']
        read_only_fields = fields


class VarianceAdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VarianceAdjustment
        fields = ['variance_id', 'payment', 'original_amount', 'adjusted_amount', 
                  'variance_amount', 'reason', 'status', 'approved_by', 'approved_at']
        read_only_fields = ['variance_id', 'status', 'approved_by', 'approved_at']


class ReplenishmentRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReplenishmentRequest
        fields = ['request_id', 'fund', 'current_balance', 'requested_amount', 
                  'status', 'auto_triggered', 'created_at']
        read_only_fields = fields


# ============================================================================
# ViewSets
# ============================================================================

class TreasuryFundViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Retrieve treasury fund information and balance.
    Requires: 
    - User must have 'treasury' app assigned
    - treasury.view_treasuryfund permission
    
    Actions:
    - list: Get all funds
    - retrieve: Get specific fund
    - balance: Get current balance for a fund
    """
    queryset = TreasuryFund.objects.all()
    serializer_class = TreasuryFundSerializer
    permission_classes = [IsAuthenticated, RequireAppAccess, DjangoModelPermissionsWithView]
    required_app = 'treasury'
    lookup_field = 'fund_id'
    
    @action(detail=True, methods=['get'])
    def balance(self, request, fund_id=None):
        """Get current balance for a fund."""
        fund = self.get_object()
        return Response({
            'fund_id': str(fund.fund_id),
            'current_balance': str(fund.current_balance),
            'reorder_level': str(fund.reorder_level),
            'needs_replenishment': fund.check_reorder_needed(),
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def replenish(self, request, fund_id=None):
        """
        Manually replenish fund (treasury staff only).
        
        Request body:
        {
            "amount": "50000.00"
        }
        """
        fund = self.get_object()
        
        # Check permission: treasury staff or admin
        user_role = request.user.role.lower() if request.user.role else ''
        if user_role not in ['treasury', 'admin']:
            return Response(
                {'error': 'Only treasury staff can replenish funds'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        amount = request.data.get('amount')
        if not amount:
            return Response(
                {'error': 'Amount is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from decimal import Decimal
            amount = Decimal(amount)
            if amount <= 0:
                return Response(
                    {'error': 'Amount must be positive'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            fund.current_balance += amount
            fund.last_replenished = timezone.now()
            fund.save(update_fields=['current_balance', 'last_replenished'])
            
            # Create ledger entry
            LedgerEntry.objects.create(
                fund=fund,
                entry_type='credit',
                amount=amount,
                description=f"Manual replenishment by {request.user.get_full_name()}",
                created_by=request.user,
            )
            
            return Response({
                'message': f'Fund replenished with {amount}',
                'new_balance': str(fund.current_balance),
            })
        
        except Exception as e:
            return Response(
                {'error': f'Replenishment failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class PaymentViewSet(viewsets.ModelViewSet):
    """
    Payment lifecycle management.
    Requires:
    - User must have 'treasury' app assigned
    - treasury permissions (view_payment, add_payment, change_payment, delete_payment)
    
    Actions:
    - list: Get all payments
    - retrieve: Get payment details
    - execute: Execute payment (with 2FA)
    - send_otp: Send OTP for payment
    - verify_otp: Verify OTP
    - reconcile: Mark as reconciled (finance staff)
    - record_variance: Record payment variance
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated, RequireAppAccess, DjangoModelPermissionsWithView]
    required_app = 'treasury'
    lookup_field = 'payment_id'
    
    def get_queryset(self):
        """Filter payments based on user role and company."""
        user = self.request.user
        # Start with company-scoped queryset
        base_qs = Payment.objects.current_company()
        
        user_role = user.role.lower() if user.role else ''
        if user_role in ['treasury', 'admin']:
            return base_qs
        # Non-staff can only see their requisitions' payments
        return base_qs.filter(requisition__requested_by=user)
    
    @action(detail=True, methods=['post'])
    def send_otp(self, request, payment_id=None):
        """Send OTP to payment executor."""
        payment = self.get_object()
        
        # Check if OTP already sent and valid
        if payment.otp_sent_timestamp and not OTPService.is_otp_expired(payment):
            return Response(
                {'warning': 'OTP already sent. Check your email. Expires in 5 minutes.'},
                status=status.HTTP_200_OK
            )
        
        success, message = PaymentExecutionService.send_otp(payment)
        return Response(
            {'success': success, 'message': message},
            status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'])
    def verify_otp(self, request, payment_id=None):
        """
        Verify OTP for 2FA.
        
        Request body:
        {
            "otp": "123456"
        }
        """
        payment = self.get_object()
        otp = request.data.get('otp', '').strip()
        
        if not otp or len(otp) != 6:
            return Response(
                {'error': 'OTP must be 6 digits'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, message = PaymentExecutionService.verify_otp(payment, otp)
        return Response(
            {'success': success, 'message': message},
            status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'])
    def execute(self, request, payment_id=None):
        """
        Execute payment with atomic transaction.
        
        Requires:
        - OTP verification (if otp_required=True)
        - Executor segregation (executor ≠ requester)
        - Sufficient fund balance
        
        Optional request body:
        {
            "gateway_reference": "GATEWAY_REF_123",
            "gateway_status": "success"
        }
        """
        payment = self.get_object()
        executor = request.user
        
        # Get optional gateway info
        gateway_ref = request.data.get('gateway_reference', '')
        gateway_status = request.data.get('gateway_status', 'success')
        ip_address = request.META.get('REMOTE_ADDR', '')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        success, message = PaymentExecutionService.execute_payment(
            payment=payment,
            executor_user=executor,
            gateway_reference=gateway_ref,
            gateway_status=gateway_status,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        if success:
            payment.refresh_from_db()
            serializer = self.get_serializer(payment)
            return Response(
                {'success': True, 'message': message, 'payment': serializer.data},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'success': False, 'error': message},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reconcile(self, request, payment_id=None):
        """
        Reconcile payment after gateway confirmation (finance staff only).
        """
        payment = self.get_object()
        
        user_role = request.user.role.lower() if request.user.role else ''
        if user_role not in ['treasury', 'admin']:
            return Response(
                {'error': 'Only finance staff can reconcile payments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        success, message = ReconciliationService.reconcile_payment(payment, request.user)
        return Response(
            {'success': success, 'message': message},
            status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'])
    def record_variance(self, request, payment_id=None):
        """
        Record payment amount variance for CFO review.
        
        Request body:
        {
            "original_amount": "1000.00",
            "adjusted_amount": "950.00",
            "reason": "Cashback applied by gateway"
        }
        """
        payment = self.get_object()
        
        user_role = request.user.role.lower() if request.user.role else ''
        if user_role not in ['treasury', 'admin']:
            return Response(
                {'error': 'Only staff can record variance'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        original = request.data.get('original_amount')
        adjusted = request.data.get('adjusted_amount')
        reason = request.data.get('reason', '')
        
        if not all([original, adjusted]):
            return Response(
                {'error': 'original_amount and adjusted_amount are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from decimal import Decimal
        try:
            original = Decimal(original)
            adjusted = Decimal(adjusted)
        except:
            return Response(
                {'error': 'Amounts must be valid decimals'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, message = ReconciliationService.record_variance(
            payment, original, adjusted, reason
        )
        return Response(
            {'success': success, 'message': message},
            status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
        )


class VarianceAdjustmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Variance adjustment tracking.
    
    Actions:
    - list: Get all variances
    - retrieve: Get variance details
    - approve: Approve variance (CFO only)
    """
    queryset = VarianceAdjustment.objects.all()
    serializer_class = VarianceAdjustmentSerializer
    permission_classes = [IsAuthenticated, RequireAppAccess, DjangoModelPermissionsWithView]
    required_app = treasury
    lookup_field = 'variance_id'
    
    @action(detail=True, methods=['post'])
    def approve(self, request, variance_id=None):
        """
        Approve variance adjustment (CFO only).
        """
        variance = self.get_object()
        
        # Check CFO role
        if not request.user.groups.filter(name__icontains='cfo').exists():
            return Response(
                {'error': 'Only CFO can approve variances'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        success, message = ReconciliationService.approve_variance(variance, request.user)
        variance.refresh_from_db()
        serializer = self.get_serializer(variance)
        
        return Response(
            {'success': success, 'message': message, 'variance': serializer.data},
            status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
        )


class ReplenishmentRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Replenishment request tracking.
    
    Actions:
    - list: Get all replenishment requests
    - retrieve: Get replenishment details
    """
    queryset = ReplenishmentRequest.objects.all()
    serializer_class = ReplenishmentRequestSerializer
    permission_classes = [IsAuthenticated, RequireAppAccess, DjangoModelPermissionsWithView]
    required_app = treasury
    lookup_field = 'request_id'


class LedgerEntryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Fund ledger entries for reconciliation.
    
    Actions:
    - list: Get all ledger entries
    - retrieve: Get entry details
    - by_fund: Get entries for specific fund
    """
    queryset = LedgerEntry.objects.all()
    serializer_class = LedgerEntrySerializer
    permission_classes = [IsAuthenticated, RequireAppAccess, DjangoModelPermissionsWithView]
    required_app = treasury
    lookup_field = 'ledger_id'
    
    @action(detail=False, methods=['get'])
    def by_fund(self, request):
        """Get ledger entries for a specific fund."""
        fund_id = request.query_params.get('fund_id')
        if not fund_id:
            return Response(
                {'error': 'fund_id query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        entries = LedgerEntry.objects.filter(fund__fund_id=fund_id).order_by('-created_at')
        serializer = self.get_serializer(entries, many=True)
        return Response(serializer.data)


# ============================================================================
# PHASE 6: DASHBOARD & REPORTING VIEWS
# ============================================================================

from treasury.models import (
    TreasuryDashboard, DashboardMetric, Alert, PaymentTracking, FundForecast
)
from treasury.services.dashboard_service import DashboardService
from treasury.services.alert_service import AlertService
from treasury.services.report_service import ReportService


# Serializers for Phase 6

class TreasuryDashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = TreasuryDashboard
        fields = [
            'dashboard_id', 'company', 'total_funds', 'total_balance', 'total_utilization_pct',
            'funds_below_reorder', 'funds_critical', 'payments_today', 'payments_this_week',
            'payments_this_month', 'total_amount_today', 'total_amount_this_week',
            'total_amount_this_month', 'active_alerts', 'critical_alerts',
            'pending_replenishments', 'pending_replenishment_amount', 'pending_variances',
            'pending_variance_amount', 'calculated_at'
        ]
        read_only_fields = fields


class DashboardMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardMetric
        fields = ['metric_id', 'metric_type', 'metric_date', 'metric_hour', 'value', 'created_at']
        read_only_fields = fields


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = [
            'alert_id', 'alert_type', 'severity', 'title', 'message',
            'related_payment', 'related_fund', 'related_variance',
            'created_at', 'acknowledged_at', 'resolved_at', 'resolution_notes',
            'email_sent', 'email_sent_at'
        ]
        read_only_fields = [
            'alert_id', 'created_at', 'acknowledged_at', 'resolved_at'
        ]


class PaymentTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTracking
        fields = [
            'tracking_id', 'payment', 'current_status', 'status_message',
            'created_at', 'otp_sent_at', 'otp_verified_at', 'execution_started_at',
            'execution_completed_at', 'total_execution_time', 'otp_verification_time'
        ]
        read_only_fields = fields


class FundForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundForecast
        fields = [
            'forecast_id', 'fund', 'forecast_date', 'predicted_balance',
            'predicted_utilization_pct', 'predicted_daily_expense', 'days_until_reorder',
            'needs_replenishment', 'recommended_replenishment_amount', 'confidence_level',
            'forecast_horizon_days', 'calculated_at'
        ]
        read_only_fields = fields


# ViewSets for Phase 6

class DashboardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Dashboard metrics and aggregates.
    
    Actions:
    - list: Get all dashboards
    - retrieve: Get dashboard for company
    - summary: Get dashboard summary with all metrics
    - fund_status: Get fund status cards
    - pending_payments: Get pending payments ready to execute
    - recent_payments: Get recent executed payments
    - refresh: Force refresh dashboard cache
    """
    queryset = TreasuryDashboard.objects.all()
    serializer_class = TreasuryDashboardSerializer
    permission_classes = [IsAuthenticated, RequireAppAccess, DjangoModelPermissionsWithView]
    required_app = treasury
    lookup_field = 'dashboard_id'
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get complete dashboard summary for user's company."""
        company_id = request.user.profile.company_id if hasattr(request.user, 'profile') else None
        
        if not company_id:
            return Response(
                {'error': 'User company not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        dashboard = DashboardService.calculate_dashboard_metrics(company_id)
        serializer = self.get_serializer(dashboard)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def fund_status(self, request):
        """Get fund status cards for dashboard."""
        company_id = request.user.profile.company_id if hasattr(request.user, 'profile') else None
        
        if not company_id:
            return Response(
                {'error': 'User company not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cards = DashboardService.get_fund_status_cards(company_id)
        return Response({'fund_status': cards})
    
    @action(detail=False, methods=['get'])
    def pending_payments(self, request):
        """Get pending payments ready for execution."""
        company_id = request.user.profile.company_id if hasattr(request.user, 'profile') else None
        
        if not company_id:
            return Response(
                {'error': 'User company not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payments = DashboardService.get_pending_payments(company_id)
        serializer = PaymentSerializer(payments, many=True)
        return Response({'pending_payments': serializer.data})
    
    @action(detail=False, methods=['get'])
    def recent_payments(self, request):
        """Get recent executed payments."""
        company_id = request.user.profile.company_id if hasattr(request.user, 'profile') else None
        
        if not company_id:
            return Response(
                {'error': 'User company not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payments = DashboardService.get_recent_payments(company_id, limit=15)
        serializer = PaymentSerializer(payments, many=True)
        return Response({'recent_payments': serializer.data})
    
    @action(detail=False, methods=['post'])
    def refresh(self, request):
        """Force refresh dashboard cache for all companies."""
        count = DashboardService.refresh_dashboard_cache()
        return Response({
            'message': f'Dashboard cache refreshed for {count} companies',
            'count': count
        })


class AlertsViewSet(viewsets.ModelViewSet):
    """
    Treasury alerts and notifications.
    
    Actions:
    - list: Get all alerts
    - retrieve: Get alert details
    - active: Get active (unresolved) alerts
    - summary: Get alert summary by severity
    - acknowledge: Mark alert as acknowledged
    - resolve: Mark alert as resolved
    """
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated, RequireAppAccess, DjangoModelPermissionsWithView]
    required_app = treasury
    lookup_field = 'alert_id'
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active (unresolved) alerts."""
        company_id = request.user.profile.company_id if hasattr(request.user, 'profile') else None
        alerts = AlertService.get_unresolved_alerts(company_id=company_id)
        
        severity_filter = request.query_params.get('severity')
        if severity_filter:
            alerts = alerts.filter(severity=severity_filter)
        
        serializer = self.get_serializer(alerts, many=True)
        return Response({'active_alerts': serializer.data})
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get alert summary by severity."""
        company_id = request.user.profile.company_id if hasattr(request.user, 'profile') else None
        summary = AlertService.get_alert_summary(company_id=company_id)
        return Response({'alert_summary': summary})
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, alert_id=None):
        """Acknowledge an alert (mark as seen)."""
        alert = self.get_object()
        AlertService.acknowledge_alert(alert, request.user)
        serializer = self.get_serializer(alert)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, alert_id=None):
        """Resolve an alert with optional notes."""
        alert = self.get_object()
        notes = request.data.get('notes')
        AlertService.resolve_alert(alert, request.user, notes)
        serializer = self.get_serializer(alert)
        return Response(serializer.data)


class PaymentTrackingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Payment execution tracking and audit trail.
    
    Actions:
    - list: Get all payment tracking records
    - retrieve: Get tracking for specific payment
    - by_status: Get payments filtered by status
    """
    queryset = PaymentTracking.objects.all()
    serializer_class = PaymentTrackingSerializer
    permission_classes = [IsAuthenticated, RequireAppAccess, DjangoModelPermissionsWithView]
    required_app = treasury
    lookup_field = 'tracking_id'
    
    @action(detail=False, methods=['get'])
    def by_status(self, request):
        """Get payment tracking records filtered by status."""
        status_filter = request.query_params.get('status')
        
        if not status_filter:
            return Response(
                {'error': 'status query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tracking = PaymentTracking.objects.filter(current_status=status_filter)
        serializer = self.get_serializer(tracking, many=True)
        return Response({'tracking': serializer.data})


class ReportingViewSet(viewsets.ViewSet):
    """
    Reporting and analytics endpoints.
    
    Actions:
    - payment_summary: Get payment summary report
    - fund_health: Get fund health report
    - variance_analysis: Get variance analysis
    - forecast: Get replenishment forecast
    - export: Export report to CSV/PDF
    """
    permission_classes = [IsAuthenticated, RequireAppAccess, DjangoModelPermissionsWithView]
    required_app = treasury
    
    @action(detail=False, methods=['get'])
    def payment_summary(self, request):
        """Get payment summary report."""
        from datetime import datetime
        
        company_id = request.user.profile.company_id if hasattr(request.user, 'profile') else None
        start_date = request.query_params.get('start_date', str(timezone.now().date() - timezone.timedelta(days=30)))
        end_date = request.query_params.get('end_date', str(timezone.now().date()))
        
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        report = ReportService.generate_payment_summary(company_id, start_date, end_date)
        return Response(report)
    
    @action(detail=False, methods=['get'])
    def fund_health(self, request):
        """Get fund health report."""
        company_id = request.user.profile.company_id if hasattr(request.user, 'profile') else None
        report = ReportService.generate_fund_health_report(company_id)
        return Response(report)
    
    @action(detail=False, methods=['get'])
    def variance_analysis(self, request):
        """Get variance analysis report."""
        from datetime import datetime
        
        company_id = request.user.profile.company_id if hasattr(request.user, 'profile') else None
        start_date = request.query_params.get('start_date', str(timezone.now().date() - timezone.timedelta(days=30)))
        end_date = request.query_params.get('end_date', str(timezone.now().date()))
        
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        report = ReportService.generate_variance_analysis(company_id, start_date, end_date)
        return Response(report)
    
    @action(detail=False, methods=['get'])
    def forecast(self, request):
        """Get replenishment forecast."""
        from organization.models import Company
        
        company_id = request.user.profile.company_id if hasattr(request.user, 'profile') else None
        horizon_days = int(request.query_params.get('horizon', 30))
        
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return Response(
                {'error': 'Company not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        funds = TreasuryFund.objects.filter(company=company)
        forecasts = []
        
        for fund in funds:
            forecast = ReportService.generate_replenishment_forecast(fund, horizon_days)
            forecasts.append(FundForecastSerializer(forecast).data)
        
        return Response({'forecasts': forecasts})
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """Export report to CSV or PDF."""
        from django.http import HttpResponse
        
        report_type = request.query_params.get('type', 'payment_summary')
        export_format = request.query_params.get('format', 'csv')
        
        company_id = request.user.profile.company_id if hasattr(request.user, 'profile') else None
        
        # Generate report
        if report_type == 'payment_summary':
            from datetime import datetime
            start_date = request.query_params.get('start_date', str(timezone.now().date() - timezone.timedelta(days=30)))
            end_date = request.query_params.get('end_date', str(timezone.now().date()))
            
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid date format'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            report_data = ReportService.generate_payment_summary(company_id, start_date, end_date)
        elif report_type == 'fund_health':
            report_data = ReportService.generate_fund_health_report(company_id)
        elif report_type == 'variance_analysis':
            from datetime import datetime
            start_date = request.query_params.get('start_date', str(timezone.now().date() - timezone.timedelta(days=30)))
            end_date = request.query_params.get('end_date', str(timezone.now().date()))
            
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid date format'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            report_data = ReportService.generate_variance_analysis(company_id, start_date, end_date)
        else:
            return Response(
                {'error': 'Invalid report type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Export
        if export_format == 'csv':
            csv_data = ReportService.export_report_to_csv(report_data, report_type)
            response = HttpResponse(csv_data, content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="report_{report_type}.csv"'
            return response
        elif export_format == 'pdf':
            pdf_data = ReportService.export_report_to_pdf(report_data, report_type)
            if pdf_data:
                response = HttpResponse(pdf_data, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="report_{report_type}.pdf"'
                return response
            else:
                return Response(
                    {'error': 'PDF export not available'},
                    status=status.HTTP_501_NOT_IMPLEMENTED
                )
        else:
            return Response(
                {'error': 'Invalid export format'},
                status=status.HTTP_400_BAD_REQUEST
            )


# ============================================================================
# M-Pesa Callback Handler
# ============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def mpesa_callback(request):
    """
    Handle M-Pesa STK Push callback.
    Called by Safaricom after customer completes payment.
    
    Updates payment record with M-Pesa receipt number.
    """
    try:
        # Parse callback data
        callback_data = json.loads(request.body)
        
        # Process callback
        result = process_mpesa_callback(callback_data)
        
        if not result.get('success'):
            return JsonResponse({
                'ResultCode': 1,
                'ResultDesc': 'Callback processing failed'
            })
        
        # Find payment by checkout request ID
        checkout_request_id = result.get('checkout_request_id')
        
        try:
            payment = Payment.objects.get(mpesa_checkout_request_id=checkout_request_id)
            
            # Update payment with M-Pesa receipt
            payment.mpesa_receipt = result.get('mpesa_receipt')
            payment.status = 'success' if result.get('result_code') == 0 else 'failed'
            
            if payment.status == 'failed':
                payment.last_error = result.get('result_desc', 'M-Pesa transaction failed')
                payment.retry_count += 1
            
            payment.save(update_fields=['mpesa_receipt', 'status', 'last_error', 'retry_count'])
            
            # Update PaymentExecution record if exists
            execution = PaymentExecution.objects.filter(payment=payment).first()
            if execution:
                execution.gateway_reference = result.get('mpesa_receipt')
                execution.gateway_status = 'success' if result.get('result_code') == 0 else 'failed'
                execution.save(update_fields=['gateway_reference', 'gateway_status'])
            
            return JsonResponse({
                'ResultCode': 0,
                'ResultDesc': 'Callback processed successfully'
            })
        
        except Payment.DoesNotExist:
            return JsonResponse({
                'ResultCode': 1,
                'ResultDesc': f'Payment not found for CheckoutRequestID: {checkout_request_id}'
            })
    
    except Exception as e:
        return JsonResponse({
            'ResultCode': 1,
            'ResultDesc': f'Error processing callback: {str(e)}'
        })
