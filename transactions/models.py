import uuid
from django.db import models
from django.conf import settings
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

    transaction_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
        Resolve workflow sequence based on threshold, origin, role availability,
        no-self-approval invariant, and urgency rules.
        """
        if not self.applied_threshold:
            self.apply_threshold()

        roles_sequence = self.applied_threshold.roles_sequence
        resolved = []
        skipped_roles = []

        for role in roles_sequence:
            candidates = User.objects.filter(role=role, is_active=True)
            # Scope filtering
            if self.origin_type == 'branch' and self.branch:
                candidates = candidates.filter(branch=self.branch)
            elif self.origin_type == 'hq' and self.company:
                candidates = candidates.filter(company=self.company)
            elif self.origin_type == 'field' and self.region:
                candidates = candidates.filter(region=self.region)

            # Exclude requester (No-Self-Approval)
            candidates = candidates.exclude(id=self.requested_by.id)

            candidate = candidates.first()
            if candidate:
                resolved.append({
                    "user_id": candidate.id,
                    "role": role,
                    "auto_escalated": False
                })
            else:
                skipped_roles.append(role)  # track skipped role
                # Auto-escalate to Admin or superuser
                admin = User.objects.filter(role="admin", is_active=True).first()
                if not admin:
                    admin = User.objects.filter(is_superuser=True, is_active=True).first()
                if not admin:
                    raise ValueError("No ADMIN or superuser exists. Please create one.")
                resolved.append({
                    "user_id": admin.id,
                    "role": "admin",
                    "auto_escalated": True
                })

        # Urgency fast-track
        if self.is_urgent and self.applied_threshold.allow_urgent_fasttrack and self.tier != 'Tier 4':
            resolved = [resolved[-1]]  # Short-circuit to final approver
            skipped_roles = roles_sequence[:-1]

        if resolved:
            self.workflow_sequence = resolved
            self.next_approver = User.objects.get(id=resolved[0]["user_id"])
            self.save(update_fields=['workflow_sequence', 'next_approver'])

        # Store skipped roles for audit trail
        self._skipped_roles = skipped_roles
        return resolved

    def can_approve(self, user):
        """
        No-self-approval enforcement.
        Only the next_approver can approve.
        """
        if user.id == self.requested_by.id:
            return False
        return self.next_approver and user.id == self.next_approver.id


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
