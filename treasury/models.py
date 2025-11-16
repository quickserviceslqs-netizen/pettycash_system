import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from transactions.models import Requisition
from organization.models import Company, Region, Branch


class TreasuryFund(models.Model):
    """
    Fund balance tracker for company/region/branch.
    Maintains current cash balance and reorder levels.
    """
    fund_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='treasury_funds')
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True, related_name='treasury_funds')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='treasury_funds')
    
    current_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    reorder_level = models.DecimalField(
        max_digits=14, 
        decimal_places=2, 
        default=Decimal('50000.00'),
        help_text="Minimum balance threshold. Auto-triggers ReplenishmentRequest when exceeded."
    )
    
    last_replenished = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('company', 'region', 'branch')
        verbose_name = "Treasury Fund"
        verbose_name_plural = "Treasury Funds"
    
    def __str__(self):
        loc = f"{self.branch.name}" if self.branch else (f"{self.region.name}" if self.region else "HQ")
        return f"{self.company.name} - {loc}: {self.current_balance}"
    
    def check_reorder_needed(self):
        """Return True if balance is below reorder level."""
        return self.current_balance < self.reorder_level


class Payment(models.Model):
    """
    Payment record for a requisition.
    Tracks payment method, destination, executor, and 2FA status.
    """
    PAYMENT_METHOD_CHOICES = [
        ('mpesa', 'MPESA'),
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('executing', 'Executing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('reconciled', 'Reconciled'),
    ]
    
    payment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requisition = models.ForeignKey(Requisition, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='mpesa')
    destination = models.CharField(max_length=255, help_text="Phone number, account, or recipient name")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Executor segregation of duties
    executor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='executed_payments'
    )
    execution_timestamp = models.DateTimeField(null=True, blank=True)
    
    # 2FA
    otp_required = models.BooleanField(default=True)
    otp_sent_timestamp = models.DateTimeField(null=True, blank=True)
    otp_verified = models.BooleanField(default=False)
    otp_verified_timestamp = models.DateTimeField(null=True, blank=True)
    
    # Retry tracking
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    last_error = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['requisition', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"Payment {self.payment_id}: {self.amount} via {self.method} - {self.status}"
    
    def can_execute(self, executor_user):
        """Check if executor is allowed to execute this payment."""
        # Executor cannot be the original requester
        if executor_user.id == self.requisition.requested_by_id:
            return False
        
        # Must be Treasury, CFO, or Admin
        allowed_roles = ['treasury', 'cfo', 'admin']
        if executor_user.role.lower() not in allowed_roles:
            return False
        
        return True
    
    def mark_executing(self):
        """Transition to executing state."""
        if self.status != 'pending':
            raise ValidationError(f"Cannot execute payment in {self.status} state")
        self.status = 'executing'
        self.save()
    
    def mark_success(self, executor_user):
        """Transition to success state."""
        self.status = 'success'
        self.executor = executor_user
        self.execution_timestamp = timezone.now()
        self.save()
    
    def mark_failed(self, error_msg):
        """Transition to failed state."""
        self.status = 'failed'
        self.last_error = error_msg
        self.retry_count += 1
        self.save()


class PaymentExecution(models.Model):
    """
    Record of successful payment execution.
    Immutable audit trail with gateway response.
    """
    execution_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='execution')
    executor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='payment_executions'
    )
    execution_timestamp = models.DateTimeField(auto_now_add=True)
    
    # Gateway response
    gateway_reference = models.CharField(max_length=255, unique=True)
    gateway_status = models.CharField(max_length=50)
    
    # 2FA audit
    otp_verified_at = models.DateTimeField(null=True, blank=True)
    otp_verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='verified_payments'
    )
    
    # Request audit
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-execution_timestamp']
        verbose_name = "Payment Execution"
        verbose_name_plural = "Payment Executions"
    
    def __str__(self):
        return f"Executed {self.payment.payment_id} via {self.gateway_reference}"


class LedgerEntry(models.Model):
    """
    Immutable fund ledger for reconciliation.
    Tracks all debits/credits to treasury fund.
    """
    ENTRY_TYPE_CHOICES = [
        ('debit', 'Debit (Payment Out)'),
        ('credit', 'Credit (Replenishment In)'),
        ('adjustment', 'Adjustment (Variance)'),
    ]
    
    entry_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    treasury_fund = models.ForeignKey(TreasuryFund, on_delete=models.CASCADE, related_name='ledger_entries')
    payment_execution = models.ForeignKey(
        PaymentExecution, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='ledger_entries'
    )
    
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    
    # Reconciliation
    reconciled = models.BooleanField(default=False)
    reconciled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reconciled_entries'
    )
    reconciliation_timestamp = models.DateTimeField(null=True, blank=True)
    
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = "Ledger Entry"
        verbose_name_plural = "Ledger Entries"
    
    def __str__(self):
        return f"{self.entry_type.upper()}: {self.amount} - {self.description[:50]}"


class VarianceAdjustment(models.Model):
    """
    Record of variance between expected and actual fund balance.
    Requires CFO approval.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    adjustment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    treasury_fund = models.ForeignKey(TreasuryFund, on_delete=models.CASCADE, related_name='variances')
    
    original_amount = models.DecimalField(max_digits=14, decimal_places=2)
    adjusted_amount = models.DecimalField(max_digits=14, decimal_places=2)
    variance_amount = models.DecimalField(max_digits=14, decimal_places=2)  # adjusted - original
    
    reason = models.TextField()
    
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='initiated_adjustments'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_adjustments'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Variance Adjustment"
        verbose_name_plural = "Variance Adjustments"
    
    def __str__(self):
        return f"Variance: {self.variance_amount} ({self.status})"


class ReplenishmentRequest(models.Model):
    """
    Auto-triggered or manual request to replenish treasury fund.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('funded', 'Funded'),
        ('rejected', 'Rejected'),
    ]
    
    request_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    treasury_fund = models.ForeignKey(TreasuryFund, on_delete=models.CASCADE, related_name='replenishment_requests')
    
    current_balance = models.DecimalField(max_digits=14, decimal_places=2)
    requested_amount = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.TextField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_replenishment_requests'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Replenishment Request"
        verbose_name_plural = "Replenishment Requests"
    
    def __str__(self):
        return f"Replenish {self.requested_amount} for {self.treasury_fund} - {self.status}"
