import os
import json
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import FileExtensionValidator


class BackupRecord(models.Model):
    """
    Track all system backups with metadata for restoration.
    """
    BACKUP_TYPE_CHOICES = [
        ('full', 'Full Backup'),
        ('incremental', 'Incremental Backup'),
        ('database_only', 'Database Only'),
        ('media_only', 'Media Files Only'),
        ('settings_only', 'Settings Only'),
        ('pre_maintenance', 'Pre-Maintenance Backup'),
        ('pre_reset', 'Pre-Factory Reset'),
        ('scheduled', 'Scheduled Backup'),
        ('manual', 'Manual Backup'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('corrupted', 'Corrupted'),
        ('verified', 'Verified'),
    ]
    
    backup_id = models.CharField(max_length=100, unique=True, editable=False)
    backup_type = models.CharField(max_length=20, choices=BACKUP_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Backup metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_backups'
    )
    
    # File information
    database_file = models.FileField(upload_to='backups/database/', null=True, blank=True)
    media_archive = models.FileField(upload_to='backups/media/', null=True, blank=True)
    settings_file = models.FileField(upload_to='backups/settings/', null=True, blank=True)
    
    # Backup details
    file_size_bytes = models.BigIntegerField(default=0, help_text="Total backup size in bytes")
    database_size_bytes = models.BigIntegerField(default=0)
    media_size_bytes = models.BigIntegerField(default=0)
    
    # Restoration metadata
    is_restorable = models.BooleanField(default=True)
    restore_tested = models.BooleanField(default=False)
    last_verified = models.DateTimeField(null=True, blank=True)
    
    # Additional metadata
    records_count = models.JSONField(
        default=dict,
        help_text="Count of records per model at backup time"
    )
    system_version = models.CharField(max_length=50, blank=True)
    django_version = models.CharField(max_length=50, blank=True)
    python_version = models.CharField(max_length=50, blank=True)
    
    # Retention
    expires_at = models.DateTimeField(null=True, blank=True)
    is_protected = models.BooleanField(
        default=False,
        help_text="Protected backups won't be auto-deleted"
    )
    
    # Error tracking
    error_message = models.TextField(blank=True)
    completion_time = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)
    
    # Notes
    description = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['backup_type']),
        ]
    
    def __str__(self):
        return f"{self.backup_id} - {self.get_backup_type_display()} ({self.status})"
    
    def get_size_display(self):
        """Human-readable file size"""
        size = self.file_size_bytes
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
    
    def mark_completed(self):
        """Mark backup as completed"""
        self.status = 'completed'
        self.completion_time = timezone.now()
        if self.created_at:
            self.duration_seconds = int((self.completion_time - self.created_at).total_seconds())
        self.save()
    
    def mark_failed(self, error):
        """Mark backup as failed with error"""
        self.status = 'failed'
        self.error_message = str(error)
        self.completion_time = timezone.now()
        self.save()


class RestorePoint(models.Model):
    """
    Snapshot of system state for point-in-time recovery.
    """
    STATUS_CHOICES = [
        ('ready', 'Ready'),
        ('restoring', 'Restoring'),
        ('restored', 'Restored'),
        ('failed', 'Failed'),
        ('superseded', 'Superseded'),
    ]
    
    restore_point_id = models.CharField(max_length=100, unique=True, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Associated backup
    backup = models.ForeignKey(
        BackupRecord, 
        on_delete=models.CASCADE,
        related_name='restore_points'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ready')
    
    # System state snapshot
    system_state = models.JSONField(
        default=dict,
        help_text="Snapshot of critical system settings and state"
    )
    
    # Restoration tracking
    last_restored_at = models.DateTimeField(null=True, blank=True)
    last_restored_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='restored_points',
        blank=True
    )
    restore_count = models.IntegerField(default=0)
    
    is_automatic = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class MaintenanceMode(models.Model):
    """
    Control system-wide maintenance mode.
    """
    is_active = models.BooleanField(default=False)
    
    # Activation details
    activated_at = models.DateTimeField(null=True, blank=True)
    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='activated_maintenance'
    )
    
    # Deactivation details
    deactivated_at = models.DateTimeField(null=True, blank=True)
    deactivated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='deactivated_maintenance',
        blank=True
    )
    
    # Maintenance details
    reason = models.TextField(help_text="Reason for maintenance")
    estimated_duration_minutes = models.IntegerField(
        default=30,
        help_text="Estimated maintenance duration"
    )
    expected_completion = models.DateTimeField(null=True, blank=True)
    
    # Backup before maintenance
    pre_maintenance_backup = models.ForeignKey(
        BackupRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maintenance_sessions'
    )
    
    # Notifications
    notify_users = models.BooleanField(default=True)
    custom_message = models.TextField(
        blank=True,
        help_text="Custom message to display during maintenance"
    )
    
    # Completion
    completed_successfully = models.BooleanField(default=False)
    completion_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-activated_at']
        get_latest_by = 'activated_at'
        permissions = (
            ('manage_maintenance', 'Can manage maintenance sessions and settings'),
        )
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"Maintenance Mode - {status}"
    
    @classmethod
    def is_maintenance_active(cls):
        """Check if maintenance mode is currently active"""
        try:
            latest = cls.objects.latest()
            return latest.is_active
        except cls.DoesNotExist:
            return False
    
    def activate(self, user, reason, duration_minutes=30, backup=None):
        """Activate maintenance mode"""
        self.is_active = True
        self.activated_at = timezone.now()
        self.activated_by = user
        self.reason = reason
        self.estimated_duration_minutes = duration_minutes
        self.expected_completion = self.activated_at + timezone.timedelta(minutes=duration_minutes)
        self.pre_maintenance_backup = backup
        self.save()
    
    def deactivate(self, user, success=True, notes=''):
        """Deactivate maintenance mode"""
        self.is_active = False
        self.deactivated_at = timezone.now()
        self.deactivated_by = user
        self.completed_successfully = success
        self.completion_notes = notes
        self.save()


class SystemHealthCheck(models.Model):
    """
    Track system health checks and critical issues.
    """
    SEVERITY_CHOICES = [
        ('critical', 'Critical'),
        ('warning', 'Warning'),
        ('info', 'Info'),
        ('success', 'Success'),
    ]
    
    check_id = models.CharField(max_length=100, unique=True, editable=False)
    
    # Check details
    performed_at = models.DateTimeField(auto_now_add=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Results
    overall_status = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    health_score = models.IntegerField(
        default=100,
        help_text="Overall health score (0-100)"
    )
    
    # Detailed results
    checks_performed = models.JSONField(
        default=dict,
        help_text="Detailed results of individual checks"
    )
    
    # Issues found
    critical_issues = models.JSONField(default=list)
    warnings = models.JSONField(default=list)
    recommendations = models.JSONField(default=list)
    
    # System metrics
    database_size_mb = models.FloatField(default=0)
    disk_usage_percent = models.FloatField(default=0)
    memory_usage_percent = models.FloatField(default=0)
    backup_age_days = models.FloatField(default=0)
    
    # Data integrity
    orphaned_records_count = models.IntegerField(default=0)
    missing_files_count = models.IntegerField(default=0)
    
    # Performance
    avg_response_time_ms = models.FloatField(default=0)
    slow_queries_count = models.IntegerField(default=0)
    
    duration_seconds = models.FloatField(default=0)
    
    class Meta:
        ordering = ['-performed_at']
        indexes = [
            models.Index(fields=['-performed_at']),
            models.Index(fields=['overall_status']),
        ]
    
    def __str__(self):
        return f"Health Check {self.check_id} - {self.overall_status} ({self.health_score}%)"


class FactoryResetLog(models.Model):
    """
    Audit log for factory reset operations.
    """
    reset_id = models.CharField(max_length=100, unique=True, editable=False)
    
    # Reset details
    initiated_at = models.DateTimeField(auto_now_add=True)
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    
    # Pre-reset backup
    pre_reset_backup = models.ForeignKey(
        BackupRecord,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reset_operations'
    )
    
    # What was reset
    reset_database = models.BooleanField(default=False)
    reset_media_files = models.BooleanField(default=False)
    reset_settings = models.BooleanField(default=False)
    keep_users = models.BooleanField(default=False)
    keep_organizations = models.BooleanField(default=False)
    
    # Confirmation
    confirmation_code = models.CharField(max_length=50)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    
    # Execution
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending_confirmation', 'Pending Confirmation'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('cancelled', 'Cancelled'),
        ],
        default='pending_confirmation'
    )
    
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Recovery info
    recovery_backup_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Backup ID for emergency recovery"
    )
    
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-initiated_at']
    
    def __str__(self):
        return f"Factory Reset {self.reset_id} - {self.status}"
