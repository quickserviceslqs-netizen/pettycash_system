from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from organization.models import Company, Region, Branch, Department, CostCenter, Position

# Import device management models
from .models_device import UserInvitation, WhitelistedDevice, DeviceAccessAttempt


class App(models.Model):
    """
    Represents an application module that can be assigned to users.
    Replaces hardcoded ROLE_ACCESS mapping with flexible app assignments.
    """
    APP_CHOICES = [
        ('transactions', 'Transactions'),
        ('treasury', 'Treasury'),
        ('workflow', 'Workflow'),
        ('reports', 'Reports'),
    ]
    
    name = models.CharField(
        max_length=50, 
        choices=APP_CHOICES, 
        unique=True,
        help_text="Internal app name (lowercase)"
    )
    display_name = models.CharField(
        max_length=100,
        help_text="User-friendly display name"
    )
    url = models.CharField(
        max_length=200,
        help_text="URL path for this app (e.g., /transactions/)"
    )
    description = models.TextField(
        blank=True,
        help_text="What this app does"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this app is currently available"
    )
    
    class Meta:
        ordering = ['display_name']
        verbose_name = "Application"
        verbose_name_plural = "Applications"
    
    def __str__(self):
        return self.display_name
    
    def save(self, *args, **kwargs):
        # Auto-set display name and URL from choices if not provided
        if not self.display_name:
            self.display_name = self.name.capitalize()
        if not self.url:
            self.url = f"/{self.name}/"
        super().save(*args, **kwargs)


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
    
    # ✅ Flexible app assignments - replace hardcoded ROLE_ACCESS
    # Users can be assigned specific apps, and Django permissions control what they can do within those apps
    assigned_apps = models.ManyToManyField(
        App,
        blank=True,
        related_name='users',
        help_text="Applications this user has access to. Use Django permissions to control add/view/change/delete within each app."
    )

    # Security tracking
    failed_login_attempts = models.PositiveIntegerField(default=0)
    lockout_until = models.DateTimeField(null=True, blank=True)
    last_failed_login = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_login_user_agent = models.TextField(blank=True)

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

class UserAuditLog(models.Model):
    """
    Tracks administrative actions performed on user accounts.
    Records who did what, when, and what changed.
    """
    ACTION_CHOICES = [
        ('create', 'User Created'),
        ('update', 'User Updated'),
        ('delete', 'User Deleted'),
        ('activate', 'User Activated'),
        ('deactivate', 'User Deactivated'),
        ('password_reset', 'Password Reset Sent'),
        ('role_change', 'Role Changed'),
        ('app_assign', 'Apps Assigned'),
        ('permission_change', 'Permissions Changed'),
        ('group_change', 'Groups Changed'),
    ]
    
    target_user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='audit_logs',
        help_text="User who was affected by this action"
    )
    performed_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='performed_audits',
        help_text="Admin who performed the action"
    )
    action = models.CharField(
        max_length=30,
        choices=ACTION_CHOICES,
        help_text="Type of action performed"
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        help_text="When the action occurred"
    )
    changes = models.JSONField(
        null=True,
        blank=True,
        help_text="Details of what changed (before/after values)"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional context or reason for the change"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the admin who made the change"
    )
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "User Audit Log"
        verbose_name_plural = "User Audit Logs"
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['target_user', '-timestamp']),
            models.Index(fields=['performed_by', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} on {self.target_user.username} by {self.performed_by} at {self.timestamp}"

