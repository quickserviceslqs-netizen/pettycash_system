"""
Device and Invitation Management Models
Handles user invitations and device whitelisting for security
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail
from django.urls import reverse
import uuid
import secrets


class UserInvitation(models.Model):
    """
    Email invitation sent to new users.
    Users click link to create their account and their device is automatically whitelisted.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
    ]
    
    # Invitation details
    email = models.EmailField(
        help_text="Email address to send invitation to"
    )
    first_name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Recipient's first name"
    )
    last_name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Recipient's last name"
    )
    role = models.CharField(
        max_length=30,
        help_text="Role to assign when user accepts invitation"
    )
    
    # Invitation token (secure random string)
    token = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text="Unique token for invitation link"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text="Invitation expiration date/time"
    )
    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When invitation was accepted"
    )
    
    # Relationships
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='invitations_sent',
        help_text="Admin who sent this invitation"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='invitations_received',
        help_text="User account created from this invitation"
    )
    
    # Organization assignments (optional, can be set during invitation)
    company = models.ForeignKey(
        'organization.Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    department = models.ForeignKey(
        'organization.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    branch = models.ForeignKey(
        'organization.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Apps to assign
    assigned_apps = models.JSONField(
        default=list,
        blank=True,
        help_text="List of app names to assign when user accepts"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "User Invitation"
        verbose_name_plural = "User Invitations"
    
    def __str__(self):
        return f"Invitation to {self.email} ({self.status})"
    
    def is_valid(self):
        """Check if invitation is still valid (not expired, not already accepted)"""
        if self.status != 'pending':
            return False
        if timezone.now() > self.expires_at:
            self.status = 'expired'
            self.save()
            return False
        return True
    
    def get_signup_url(self):
        """Generate signup URL with token"""
        return reverse('signup', kwargs={'token': str(self.token)})
    
    def send_invitation_email(self):
        """Send invitation email to user"""
        signup_url = f"{settings.SITE_URL}{self.get_signup_url()}" if hasattr(settings, 'SITE_URL') else self.get_signup_url()
        
        subject = f"You've been invited to join {getattr(settings, 'SITE_NAME', 'Petty Cash System')}"
        
        message = f"""
Hello {self.first_name or 'there'},

You've been invited to join our Petty Cash Management System as a {self.get_role_display()}.

To complete your registration and set up your account, please click the link below:

{signup_url}

This invitation will expire on {self.expires_at.strftime('%B %d, %Y at %I:%M %p')}.

Important Security Notes:
- Your device will be automatically registered when you complete signup
- You can only sign up from approved locations (if IP whitelist is enabled)
- Make sure to use a strong password

If you did not expect this invitation, please ignore this email.

Best regards,
The Petty Cash System Team
"""
        
        html_message = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #2c3e50;">Welcome to Petty Cash System!</h2>
    
    <p>Hello {self.first_name or 'there'},</p>
    
    <p>You've been invited to join our Petty Cash Management System as a <strong>{self.get_role_display()}</strong>.</p>
    
    <div style="margin: 30px 0;">
        <a href="{signup_url}" 
           style="background-color: #3498db; color: white; padding: 12px 24px; 
                  text-decoration: none; border-radius: 5px; display: inline-block;">
            Complete Your Registration
        </a>
    </div>
    
    <p><small>Or copy this link: <a href="{signup_url}">{signup_url}</a></small></p>
    
    <p style="color: #e74c3c; margin-top: 20px;">
        <strong>⏰ This invitation expires on {self.expires_at.strftime('%B %d, %Y at %I:%M %p')}</strong>
    </p>
    
    <div style="background-color: #ecf0f1; padding: 15px; border-left: 4px solid #3498db; margin: 20px 0;">
        <h4 style="margin-top: 0;">🔒 Security Notes:</h4>
        <ul style="margin: 10px 0;">
            <li>Your device will be automatically registered when you complete signup</li>
            <li>You can only sign up from approved locations (if IP whitelist is enabled)</li>
            <li>Make sure to use a strong password</li>
        </ul>
    </div>
    
    <p style="color: #7f8c8d; font-size: 12px; margin-top: 30px;">
        If you did not expect this invitation, please ignore this email.
    </p>
    
    <hr style="border: none; border-top: 1px solid #ecf0f1; margin: 20px 0;">
    <p style="color: #95a5a6; font-size: 12px;">
        Best regards,<br>
        The Petty Cash System Team
    </p>
</body>
</html>
"""
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.email],
                html_message=html_message,
                fail_silently=False,
            )
            return True
        except Exception as e:
            print(f"Error sending invitation email: {e}")
            return False


class WhitelistedDevice(models.Model):
    """
    Tracks whitelisted devices per user.
    Devices are automatically registered during signup or can be added manually.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='whitelisted_devices'
    )
    
    # Device identification
    device_name = models.CharField(
        max_length=255,
        help_text="Friendly device name (e.g., 'Windows 10 - Chrome')"
    )
    user_agent = models.TextField(
        help_text="Full user agent string"
    )
    ip_address = models.GenericIPAddressField(
        help_text="IP address when device was registered"
    )
    
    # Device fingerprint (optional - for advanced tracking)
    device_fingerprint = models.CharField(
        max_length=64,
        blank=True,
        help_text="Hash of device characteristics (screen resolution, timezone, etc.)"
    )
    
    # Location information
    location = models.CharField(
        max_length=255,
        blank=True,
        help_text="Location when device was registered (City, Country)"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this device is currently allowed"
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Is this the user's primary device?"
    )
    
    # Tracking
    registered_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(
        auto_now=True,
        help_text="Last time this device was used to access the system"
    )
    
    # Registration method
    REGISTRATION_METHOD_CHOICES = [
        ('signup', 'During Signup'),
        ('manual', 'Manual Addition'),
        ('self_service', 'Self-Service Portal'),
    ]
    registration_method = models.CharField(
        max_length=20,
        choices=REGISTRATION_METHOD_CHOICES,
        default='signup'
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Admin notes about this device"
    )
    
    class Meta:
        ordering = ['-is_primary', '-last_used_at']
        verbose_name = "Whitelisted Device"
        verbose_name_plural = "Whitelisted Devices"
        unique_together = ['user', 'user_agent', 'ip_address']
    
    def __str__(self):
        primary = " (Primary)" if self.is_primary else ""
        return f"{self.user.username} - {self.device_name}{primary}"
    
    def deactivate(self):
        """Deactivate this device"""
        self.is_active = False
        self.save()
    
    def activate(self):
        """Activate this device"""
        self.is_active = True
        self.save()
    
    def set_as_primary(self):
        """Set this as the user's primary device"""
        # Remove primary flag from all other devices
        WhitelistedDevice.objects.filter(user=self.user).update(is_primary=False)
        self.is_primary = True
        self.save()


class DeviceAccessAttempt(models.Model):
    """
    Logs all device access attempts (successful and blocked).
    Used for security monitoring and anomaly detection.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='device_access_attempts'
    )
    
    # Attempt details
    ip_address = models.GenericIPAddressField()
    device_name = models.CharField(max_length=255)
    user_agent = models.TextField()
    location = models.CharField(max_length=255, blank=True)
    
    # Result
    was_allowed = models.BooleanField(
        help_text="Whether access was granted"
    )
    reason = models.CharField(
        max_length=255,
        blank=True,
        help_text="Reason for allow/block decision"
    )
    
    # Timestamps
    attempted_at = models.DateTimeField(auto_now_add=True)
    
    # Request details
    request_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="URL path being accessed"
    )
    
    class Meta:
        ordering = ['-attempted_at']
        verbose_name = "Device Access Attempt"
        verbose_name_plural = "Device Access Attempts"
        indexes = [
            models.Index(fields=['-attempted_at']),
            models.Index(fields=['user', '-attempted_at']),
            models.Index(fields=['was_allowed', '-attempted_at']),
        ]
    
    def __str__(self):
        status = "✓ Allowed" if self.was_allowed else "✗ Blocked"
        return f"{status} - {self.user or 'Unknown'} from {self.ip_address}"
