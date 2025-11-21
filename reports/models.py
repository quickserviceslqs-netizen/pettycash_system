# reports/models.py
from django.db import models
from django.conf import settings
from organization.models import Company

class Report(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    ]

    title = models.CharField(max_length=200)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Multi-Tenancy: Company-aware manager (uncomment when ready)
    # from pettycash_system.managers import CompanyManager
    # objects = CompanyManager()

    def __str__(self):
        return f"{self.title} ({self.status})"
