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
"""

from rest_framework import viewsets, serializers, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from treasury.models import (
    Payment, PaymentExecution, TreasuryFund, 
    LedgerEntry, VarianceAdjustment, ReplenishmentRequest
)
from treasury.services.payment_service import (
    PaymentExecutionService, ReconciliationService, OTPService
)


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
    
    Actions:
    - list: Get all funds
    - retrieve: Get specific fund
    - balance: Get current balance for a fund
    """
    queryset = TreasuryFund.objects.all()
    serializer_class = TreasuryFundSerializer
    permission_classes = [IsAuthenticated]
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
        if not (request.user.is_staff or request.user.is_superuser):
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
    permission_classes = [IsAuthenticated]
    lookup_field = 'payment_id'
    
    def get_queryset(self):
        """Filter payments based on user role."""
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Payment.objects.all()
        # Non-staff can only see their requisitions' payments
        return Payment.objects.filter(requisition__requester=user)
    
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
        
        if not (request.user.is_staff or request.user.is_superuser):
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
        
        if not (request.user.is_staff or request.user.is_superuser):
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
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
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
