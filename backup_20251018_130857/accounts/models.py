from django.contrib.auth.models import AbstractUser
from django.db import models
from organization.models import Company, Region, Branch, Department, CostCenter, Position

class User(AbstractUser):
    ROLE_CHOICES = [
        ('staff', 'Staff'),
        ('department_head', 'Department Head'),
        ('branch_manager', 'Branch Manager'),
        ('regional_manager', 'Regional Manager'),
        ('group_finance_manager', 'Group Finance Manager'),
        ('treasury', 'Treasury'),
        ('cfo', 'CFO'),
        ('fp&a', 'FP&A'),
        ('ceo', 'CEO'),
        ('admin', 'Admin'),
    ]

    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='staff')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, null=True, blank=True)
    position_title = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"
