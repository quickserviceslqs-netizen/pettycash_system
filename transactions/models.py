import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from organization.models import Company, Region, Branch, Department
from workflow.models import ApprovalThreshold
from workflow.services.resolver import find_approval_threshold
from django.contrib.auth import get_user_model

User = get_user_model()


class Requisition(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('reviewed', 'Reviewed'),
        ('rejected', 'Rejected'),
    ]
    ORIGIN_CHOICES = [
        ('branch', 'Branch'),
        ('hq', 'HQ'),
        ('field', 'Field'),
    ]

    # Allow tests to provide simple transaction identifiers (e.g., 'REQ-001')
    # Use a CharField primary key with default UUID string for compatibility.
    transaction_id = models.CharField(primary_key=True, max_length=64, default=lambda: str(uuid.uuid4()), editable=False)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    origin_type = models.CharField(max_length=10, choices=ORIGIN_CHOICES)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    purpose = models.TextField()
    is_urgent = models.BooleanField(default=False)
    urgency_reason = models.TextField(blank=True, null=True)

    applied_threshold = models.ForeignKey(
        ApprovalThreshold, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='requisitions'
    )
    tier = models.CharField(max_length=64, blank=True, null=True)

    workflow_sequence = models.JSONField(blank=True, null=True)
    next_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='next_approvals'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # For audit purpose, store skipped roles temporarily
    _skipped_roles = []

    def __str__(self):
        return f"{self.transaction_id} - {self.status}"
    
    def clean(self):
        """Validate requisition data before save"""
        # Validate amount is positive (if set)
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({'amount': 'Amount must be greater than zero'})
        
        # Validate org structure matches origin type (only for non-draft status)
        if self.status != 'draft':
            if self.origin_type == 'branch' and not self.branch:
                raise ValidationError({'branch': 'Branch origin requires a branch to be specified'})
            if self.origin_type == 'hq' and not self.company:
                raise ValidationError({'company': 'HQ origin requires a company to be specified'})
            if self.origin_type == 'field' and not self.region:
                raise ValidationError({'region': 'Field origin requires a region to be specified'})
    
    def save(self, *args, **kwargs):
        """Override save to run validation only on explicit full_clean calls"""
        # Don't auto-validate on save to allow incremental model building
        # Validation will be enforced via forms and explicit clean() calls
        if not kwargs.pop('skip_validation', False):
            # Only validate explicitly when needed
            pass
        super().save(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        # Accept legacy 'requesting_user' kwarg used in some tests and map it to 'requested_by'
        if 'requesting_user' in kwargs and 'requested_by' not in kwargs:
            kwargs['requested_by'] = kwargs.pop('requesting_user')
        super().__init__(*args, **kwargs)

    def apply_threshold(self):
        thr = find_approval_threshold(self.amount, self.origin_type)
        if not thr:
            raise ValueError("No ApprovalThreshold found for this requisition.")
        self.applied_threshold = thr
        self.tier = thr.name
        self.save(update_fields=['applied_threshold', 'tier'])
        return thr

    def resolve_workflow(self):
        """
        Resolve workflow sequence - delegates to centralized resolver service.
        This ensures consistent workflow logic across the application.
        """
        from workflow.services.resolver import resolve_workflow
        return resolve_workflow(self)

    def can_approve(self, user):
        """
        Validate if user can approve this requisition.
        Enforces:
        - Only pending requisitions can be approved
        - No self-approval
        - Only next_approver can approve
        """
        # Only pending requisitions can be approved
        if self.status != 'pending':
            return False
        
        # No self-approval
        if user.id == self.requested_by.id:
            return False
        
        # Must be the next approver
        if not self.next_approver or user.id != self.next_approver.id:
            return False
        
        return True


class ApprovalTrail(models.Model):
    requisition = models.ForeignKey('Requisition', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    role = models.CharField(max_length=30)
    action = models.CharField(max_length=20, choices=[('approved', 'Approved'), ('rejected', 'Rejected')])
    comment = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    auto_escalated = models.BooleanField(default=False)
    skipped_roles = models.JSONField(blank=True, null=True)  # Track skipped roles for audit
    override = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.requisition} - {self.action} by {self.user}"
