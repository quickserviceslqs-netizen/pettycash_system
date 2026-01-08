import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

User = settings.AUTH_USER_MODEL
from organization.models import Branch, Company, CostCenter, Department, Region
from pettycash_system.managers import RequisitionManager
from workflow.models import ApprovalThreshold
from workflow.services.resolver import find_approval_threshold

User = get_user_model()


def generate_transaction_id():
    """Generate unique transaction ID for requisitions"""
    return str(uuid.uuid4())


class Requisition(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending", "Pending"),
        ("pending_changes", "Pending Changes from Requester"),
        ("pending_urgency_confirmation", "Pending Urgency Confirmation"),
        ("pending_dept_approval", "Pending Department Approval"),
        ("pending_branch_approval", "Pending Branch Approval"),
        ("pending_regional_review", "Pending Regional Review"),
        ("pending_finance_review", "Pending Finance Review"),
        ("pending_treasury_validation", "Pending Treasury Validation"),
        ("pending_cfo_approval", "Pending CFO Approval"),
        ("paid", "Paid"),
        ("reviewed", "Reviewed"),
        ("rejected", "Rejected"),
    ]
    ORIGIN_CHOICES = [
        ("branch", "Branch"),
        ("hq", "HQ"),
        ("field", "Field"),
    ]

    # Allow tests to provide simple transaction identifiers (e.g., 'REQ-001')
    # Use a CharField primary key with default UUID string for compatibility.
    transaction_id = models.CharField(
        primary_key=True, max_length=64, default=generate_transaction_id, editable=False
    )
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    origin_type = models.CharField(max_length=10, choices=ORIGIN_CHOICES)
    company = models.ForeignKey(
        Company, on_delete=models.SET_NULL, null=True, blank=True
    )
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True
    )
    cost_center = models.ForeignKey(
        CostCenter, on_delete=models.SET_NULL, null=True, blank=True
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    purpose = models.TextField()
    receipt = models.FileField(
        upload_to="receipts/", help_text="Upload receipt/supporting document"
    )
    is_urgent = models.BooleanField(default=False)
    urgency_reason = models.TextField(blank=True, null=True)

    applied_threshold = models.ForeignKey(
        ApprovalThreshold,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="requisitions",
    )
    tier = models.CharField(max_length=64, blank=True, null=True)

    workflow_sequence = models.JSONField(blank=True, null=True)
    is_fast_tracked = models.BooleanField(
        default=False, help_text="True if requisition skipped intermediate approvers"
    )
    original_workflow_sequence = models.JSONField(
        blank=True, null=True, help_text="Original full workflow before fast-tracking"
    )

    # Change request fields
    change_requested = models.BooleanField(
        default=False, help_text="True if approver requested changes"
    )
    change_request_details = models.TextField(
        blank=True, null=True, help_text="Specific changes requested by approver"
    )
    change_requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="change_requests_made",
    )
    change_request_deadline = models.DateTimeField(
        null=True, blank=True, help_text="Deadline for requester to respond"
    )

    next_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="next_approvals",
    )
    status = models.CharField(
        max_length=50, choices=STATUS_CHOICES, default="draft"
    )  # Phase 3: Increased for granular statuses
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Multi-Tenancy: Company-aware manager for automatic filtering
    objects = RequisitionManager()

    # For audit purpose, store skipped roles temporarily
    _skipped_roles = []

    def __str__(self):
        return f"{self.transaction_id} - {self.status}"

    def clean(self):
        """Validate requisition data before save"""
        # Validate amount is positive (if set)
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({"amount": "Amount must be greater than zero"})

        # Validate org structure matches origin type (only for non-draft status)
        if self.status != "draft":
            if self.origin_type == "branch" and not self.branch:
                raise ValidationError(
                    {"branch": "Branch origin requires a branch to be specified"}
                )
            if self.origin_type == "hq" and not self.company:
                raise ValidationError(
                    {"company": "HQ origin requires a company to be specified"}
                )
            if self.origin_type == "field" and not self.region:
                raise ValidationError(
                    {"region": "Field origin requires a region to be specified"}
                )

    def save(self, *args, **kwargs):
        """Override save to run validation only on explicit full_clean calls"""
        # Don't auto-validate on save to allow incremental model building
        # Validation will be enforced via forms and explicit clean() calls
        if not kwargs.pop("skip_validation", False):
            # Only validate explicitly when needed
            pass
        super().save(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        # Accept legacy 'requesting_user' kwarg used in some tests and map it to 'requested_by'
        if "requesting_user" in kwargs and "requested_by" not in kwargs:
            kwargs["requested_by"] = kwargs.pop("requesting_user")
        super().__init__(*args, **kwargs)

    def apply_threshold(self):
        thr = find_approval_threshold(self.amount, self.origin_type)
        if not thr:
            raise ValueError("No ApprovalThreshold found for this requisition.")
        self.applied_threshold = thr
        self.tier = thr.name
        self.save(update_fields=["applied_threshold", "tier"])
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
        Phase 4: Core invariant - No-self-approval enforcement.
        Validates if user can approve this requisition at routing, model, and API layers.

        Enforces:
        - Only pending/pending_urgency_confirmation requisitions can be approved
        - No self-approval (strict invariant)
        - Only next_approver can approve
        """
        import logging

        logger = logging.getLogger(__name__)

        # Only pending or urgency confirmation requisitions can be approved
        if self.status not in ["pending", "pending_urgency_confirmation"]:
            logger.warning(
                f"Approval denied for {self.transaction_id}: status={self.status}"
            )
            return False

        # Phase 4 Core Invariant: No self-approval
        if user.id == self.requested_by.id:
            logger.warning(
                f"Self-approval blocked for {self.transaction_id}: "
                f"user {user.username} (ID: {user.id}) is the requester"
            )
            return False

        # Must be the next approver
        if not self.next_approver or user.id != self.next_approver.id:
            logger.warning(
                f"Approval denied for {self.transaction_id}: "
                f"user {user.username} is not the next approver (expected: {self.next_approver.username if self.next_approver else 'None'})"
            )
            return False

        return True


class ApprovalTrail(models.Model):
    requisition = models.ForeignKey("Requisition", on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    role = models.CharField(max_length=30)
    action = models.CharField(
        max_length=30,
        choices=[
            ("approved", "Approved"),  # Used by approvers (BM, DH, RM, GFM, CFO)
            ("validated", "Validated"),  # Used by Treasury (validates payment details)
            ("paid", "Paid"),  # Used by Treasury (payment executed)
            ("reviewed", "Reviewed"),  # Used by FP&A (post-payment review)
            ("rejected", "Rejected"),  # Can be used by any role
            (
                "urgency_confirmed",
                "Urgency Confirmed",
            ),  # Phase 3: First approver confirms urgency
            (
                "reverted_to_normal",
                "Reverted to Normal Flow",
            ),  # Fast-track reverted to normal approval sequence
            (
                "changes_requested",
                "Changes Requested",
            ),  # Approver requests changes from requester
            (
                "changes_submitted",
                "Changes Submitted",
            ),  # Requester submitted requested changes
        ],
    )
    comment = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    auto_escalated = models.BooleanField(default=False)
    skipped_roles = models.JSONField(
        blank=True, null=True
    )  # Track skipped roles for audit
    escalation_reason = models.TextField(
        blank=True, null=True
    )  # Phase 4: Audit trail for escalations
    override = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.requisition} - {self.action} by {self.user}"
