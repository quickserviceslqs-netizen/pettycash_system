from django.contrib.auth.models import AbstractUser
from django.db import models
from organization.models import Company, Region, Branch, Department, CostCenter, Position


class User(AbstractUser):

    ROLE_CHOICES = [
        ('admin', 'Admin'),  # Business admin - handles escalations, requires company assignment
        ('staff', 'Staff'),
        ('treasury', 'Treasury'),
        ('fp&a', 'FP&A'),
        ('department_head', 'Department Head'),
        ('branch_manager', 'Branch Manager'),
        ('regional_manager', 'Regional Manager'),
        ('group_finance_manager', 'Group Finance Manager'),
        ('cfo', 'CFO'),
        ('ceo', 'CEO'),
    ]
    # Note: For Django Admin access, use Django's built-in is_superuser and is_staff fields
    # is_superuser=True → Full Django Admin access (technical staff only)
    # role='admin' → Business workflow escalations and approvals

    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='staff')

    # Organization structure fields - NOT required for superuser role
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, null=True, blank=True)
    position_title = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True)

    phone_number = models.CharField(max_length=20, blank=True, null=True)

    # ✅ New field to mark centralized/company-wide approvers
    is_centralized_approver = models.BooleanField(
        default=False,
        help_text="If True, this user can approve requisitions for the whole company regardless of branch/region/department."
    )

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def role_key(self):
        """Clean, normalized role key for permissions/dashboards."""
        return self.role.lower().strip()

    def get_display_name(self):
        """Return user's full name, or username if no name set."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return self.username

    def get_role_display(self):
        """Return the display name for the user's role."""
        return dict(self.ROLE_CHOICES).get(self.role, self.role)

    @property
    def profile(self):
        """
        Compatibility shim: some code/tests expect a `user.profile` object
        with attributes like `company`. Return self so `user.profile.company`
        maps to `user.company` without requiring a separate Profile model.
        """
        return self
