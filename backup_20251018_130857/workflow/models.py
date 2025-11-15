from django.db import models
from django.contrib.postgres.fields import JSONField  # PostgreSQL JSON support

class ApprovalThreshold(models.Model):
    min_amount = models.DecimalField(max_digits=12, decimal_places=2)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2)
    roles_sequence = models.JSONField(help_text="List of roles in approval order")  # Django 3.1+ has built-in JSONField
    allow_urgent_fasttrack = models.BooleanField(default=False)
    requires_cfo = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.min_amount} - {self.max_amount} | Roles: {self.roles_sequence}"
