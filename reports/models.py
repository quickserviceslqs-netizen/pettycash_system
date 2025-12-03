# reports/models.py
from django.db import models
from django.conf import settings
from organization.models import Company, Branch, Department, CostCenter
from pettycash_system.managers import CompanyManager

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
    
    # Multi-Tenancy: Company-aware manager
    objects = CompanyManager()

    def __str__(self):
        return f"{self.title} ({self.status})"


class BudgetAllocation(models.Model):
    """Allocated budget by scope (company/branch/department/cost center) and period."""
    PERIOD_CHOICES = [(m, m) for m in range(1, 13)]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='budgets')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='budgets')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='budgets')
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, null=True, blank=True, related_name='budgets')

    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField(choices=PERIOD_CHOICES, null=True, blank=True, help_text="If null, annual budget")
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    # Multi-Tenancy: Company-aware manager
    objects = CompanyManager()

    class Meta:
        unique_together = ('company', 'branch', 'department', 'cost_center', 'year', 'month')
        indexes = [
            models.Index(fields=['company', 'year', 'month']),
            models.Index(fields=['branch', 'department', 'cost_center']),
        ]

    def __str__(self):
        scope = (
            self.cost_center.name if self.cost_center else (
                self.department.name if self.department else (
                    self.branch.name if self.branch else self.company.name
                )
            )
        )
        period = f"{self.year}-{self.month:02d}" if self.month else f"{self.year}"
        return f"Budget {scope} {period}: {self.amount}"
