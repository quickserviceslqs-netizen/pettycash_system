import uuid
from django.db import models
from django.conf import settings
from organization.models import Company, Region, Branch, Department

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
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    purpose = models.TextField()
    is_urgent = models.BooleanField(default=False)
    urgency_reason = models.TextField(blank=True, null=True)
    tier = models.IntegerField(blank=True, null=True)
    workflow_sequence = models.JSONField(blank=True, null=True)
    next_approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='next_approvals')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.transaction_id} - {self.status}"

class ApprovalTrail(models.Model):
    requisition = models.ForeignKey(Requisition, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    role = models.CharField(max_length=30)
    action = models.CharField(max_length=20, choices=[('approved', 'Approved'), ('rejected', 'Rejected')])
    comment = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    auto_escalated = models.BooleanField(default=False)
    override = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.requisition} - {self.action} by {self.user}"
