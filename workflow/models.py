from django.db import models
from django.utils import timezone  # <-- add this

class ApprovalThreshold(models.Model):
    ORIGIN_CHOICES = [
        ('BRANCH', 'Branch'),
        ('HQ', 'HQ'),
        ('FIELD', 'Field'),
        ('ANY', 'Any'),
    ]

    name = models.CharField(max_length=128, help_text="Tier name, e.g. Tier 1, Tier 2")
    origin_type = models.CharField(max_length=16, choices=ORIGIN_CHOICES, default='ANY')
    min_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    max_amount = models.DecimalField(max_digits=14, decimal_places=2, default=999999999)
    roles_sequence = models.JSONField(
        help_text="Ordered list of roles, e.g. ['Branch Manager','Treasury']"
    )
    allow_urgent_fasttrack = models.BooleanField(
        default=False,
        help_text="If True, urgent requisitions may skip intermediate levels where allowed."
    )
    requires_cfo = models.BooleanField(
        default=False,
        help_text="True if CFO approval is mandatory (usually Tier 4)."
    )
    priority = models.PositiveIntegerField(
        default=0,
        help_text="Lower = higher priority when multiple thresholds overlap."
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now, editable=False)  # <-- updated
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', 'min_amount']
        indexes = [
            models.Index(fields=['origin_type', 'min_amount', 'max_amount']),
        ]
        verbose_name = "Approval Threshold"
        verbose_name_plural = "Approval Thresholds"

    def __str__(self):
        return f"{self.name} ({self.origin_type}: {self.min_amount}-{self.max_amount})"
