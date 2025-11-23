from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import json

User = get_user_model()


class SystemSetting(models.Model):
    """
    Store system-wide configuration settings in database.
    Allows admins to manage settings through UI instead of editing files.
    """
    CATEGORY_CHOICES = [
        ('email', 'Email Configuration'),
        ('approval', 'Approval Workflow'),
        ('payment', 'Payment Settings'),
        ('security', 'Security & Authentication'),
        ('notifications', 'Notifications'),
        ('general', 'General Settings'),
        ('reporting', 'Reports & Analytics'),
        ('requisition', 'Requisition Management'),
        ('treasury', 'Treasury Operations'),
        ('workflow', 'Workflow Automation'),
    ]
    
    SETTING_TYPE_CHOICES = [
        ('string', 'Text'),
        ('integer', 'Number'),
        ('boolean', 'True/False'),
        ('json', 'JSON/Object'),
        ('email', 'Email Address'),
        ('url', 'URL'),
    ]
    
    key = models.CharField(
        max_length=100, 
        unique=True,
        help_text="Setting identifier (e.g., DEFAULT_APPROVAL_DEADLINE_HOURS)"
    )
    display_name = models.CharField(
        max_length=200,
        help_text="Human-readable name shown in UI"
    )
    description = models.TextField(
        blank=True,
        help_text="Explanation of what this setting does"
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='general'
    )
    setting_type = models.CharField(
        max_length=20,
        choices=SETTING_TYPE_CHOICES,
        default='string'
    )
    value = models.TextField(
        help_text="Current value of the setting"
    )
    default_value = models.TextField(
        help_text="Default/fallback value"
    )
    is_sensitive = models.BooleanField(
        default=False,
        help_text="Hide value in UI (for passwords, API keys)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this setting is currently in use"
    )
    editable_by_admin = models.BooleanField(
        default=True,
        help_text="Can be changed through UI or requires code change"
    )
    requires_restart = models.BooleanField(
        default=False,
        help_text="Requires server restart to take effect"
    )
    
    last_modified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='settings_modified'
    )
    last_modified_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['category', 'display_name']
        verbose_name = "System Setting"
        verbose_name_plural = "System Settings"
        indexes = [
            models.Index(fields=['category', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.display_name} ({self.key})"
    
    def get_typed_value(self):
        """Return value converted to appropriate Python type"""
        if self.setting_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes')
        elif self.setting_type == 'integer':
            try:
                return int(self.value)
            except ValueError:
                return int(self.default_value)
        elif self.setting_type == 'json':
            try:
                return json.loads(self.value)
            except json.JSONDecodeError:
                return json.loads(self.default_value)
        else:
            return self.value
    
    def clean(self):
        """Validate setting value based on type"""
        if self.setting_type == 'integer':
            try:
                int(self.value)
            except ValueError:
                raise ValidationError({'value': 'Must be a valid integer'})
        
        elif self.setting_type == 'boolean':
            if self.value.lower() not in ('true', 'false', '1', '0', 'yes', 'no'):
                raise ValidationError({'value': 'Must be true or false'})
        
        elif self.setting_type == 'json':
            try:
                json.loads(self.value)
            except json.JSONDecodeError:
                raise ValidationError({'value': 'Must be valid JSON'})
        
        elif self.setting_type == 'email':
            from django.core.validators import validate_email
            try:
                validate_email(self.value)
            except ValidationError:
                raise ValidationError({'value': 'Must be a valid email address'})
        
        elif self.setting_type == 'url':
            from django.core.validators import URLValidator
            validator = URLValidator()
            try:
                validator(self.value)
            except ValidationError:
                raise ValidationError({'value': 'Must be a valid URL'})


class ActivityLog(models.Model):
    """
    Track all admin activities for audit purposes.
    """
    ACTION_CHOICES = [
        ('create', 'Created'),
        ('update', 'Updated'),
        ('delete', 'Deleted'),
        ('view', 'Viewed'),
        ('login', 'Logged In'),
        ('logout', 'Logged Out'),
        ('permission_change', 'Permission Changed'),
        ('setting_change', 'Setting Changed'),
        ('user_action', 'User Action'),
        ('system', 'System Action'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='activity_logs'
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    content_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Type of object affected (e.g., 'Requisition', 'User')"
    )
    object_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="ID of the affected object"
    )
    object_repr = models.CharField(
        max_length=255,
        blank=True,
        help_text="String representation of the object"
    )
    description = models.TextField(
        blank=True,
        help_text="Details about what happened"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Additional metadata
    changes = models.JSONField(
        null=True,
        blank=True,
        help_text="Before/after values for updates"
    )
    success = models.BooleanField(
        default=True,
        help_text="Whether the action succeeded"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error details if action failed"
    )
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Activity Log"
        verbose_name_plural = "Activity Logs"
        indexes = [
            models.Index(fields=['-timestamp', 'user']),
            models.Index(fields=['action', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


# Utility function to get setting value
def get_setting(key, default=None):
    """
    Get a system setting value by key.
    Returns typed value (bool, int, str, etc.)
    Falls back to default if setting doesn't exist.
    """
    try:
        setting = SystemSetting.objects.get(key=key, is_active=True)
        return setting.get_typed_value()
    except SystemSetting.DoesNotExist:
        return default
