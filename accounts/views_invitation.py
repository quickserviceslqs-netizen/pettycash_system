"""
User Invitation and Device Whitelisting Views
Handles invitation creation, signup process, and device management
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import login
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from datetime import timedelta
from accounts.models import User
from accounts.models_device import UserInvitation, WhitelistedDevice, DeviceAccessAttempt
from settings_manager.models import get_setting
from settings_manager.views import log_activity
from django.core.mail import send_mail
from django.conf import settings
import hashlib


def get_device_info(request):
    """Extract device information from request"""
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Parse device name from user agent
    device_name = "Unknown Device"
    if 'Windows' in user_agent:
        if 'Windows NT 10' in user_agent or 'Windows NT 11' in user_agent:
            device_name = "Windows 10/11"
        elif 'Windows NT 6' in user_agent:
            device_name = "Windows 7/8"
        else:
            device_name = "Windows"
    elif 'Macintosh' in user_agent or 'Mac OS X' in user_agent:
        device_name = "macOS"
    elif 'Linux' in user_agent:
        device_name = "Linux"
    elif 'Android' in user_agent:
        device_name = "Android"
    elif 'iPhone' in user_agent or 'iPad' in user_agent:
        device_name = "iOS"
    
    # Add browser info
    if 'Chrome' in user_agent and 'Edg' not in user_agent:
        device_name += " - Chrome"
    elif 'Edg' in user_agent:
        device_name += " - Edge"
    elif 'Firefox' in user_agent:
        device_name += " - Firefox"
    elif 'Safari' in user_agent and 'Chrome' not in user_agent:
        device_name += " - Safari"
    
    return {
        'device_name': device_name,
        'user_agent': user_agent
    }


def get_client_ip(request):
    """Extract client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_location(ip_address):
    """Get location from IP address using geolocation API"""
    enable_geolocation = get_setting('ENABLE_ACTIVITY_GEOLOCATION', 'true')
    
    if enable_geolocation != 'true':
        return ''
    
    try:
        import requests
        response = requests.get(
            f'http://ip-api.com/json/{ip_address}',
            timeout=2
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                city = data.get('city', '')
                region = data.get('regionName', '')
                country = data.get('country', '')
                return f"{city}, {region}, {country}" if city else f"{region}, {country}"
    except:
        pass
    
    return ''


@login_required
@permission_required('accounts.add_user', raise_exception=True)
def send_invitation(request):
    """
    Admin view to send invitation to new user.
    Creates invitation with token and sends email.
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        role = request.POST.get('role')
        company_id = request.POST.get('company')
        department_id = request.POST.get('department')
        branch_id = request.POST.get('branch')
        assigned_apps = request.POST.getlist('assigned_apps')
        
        # Validate email doesn't already exist
        if User.objects.filter(email=email).exists():
            messages.error(request, f"User with email {email} already exists!")
            return redirect('accounts:invite_user')
        
        # Check for pending invitations
        existing_pending = UserInvitation.objects.filter(
            email=email,
            status='pending'
        ).first()
        
        if existing_pending and existing_pending.is_valid():
            messages.warning(request, f"A pending invitation already exists for {email}")
            return redirect('accounts:invite_user')
        
        # Create invitation
        invitation_days = int(get_setting('INVITATION_EXPIRY_DAYS', '7'))
        expires_at = timezone.now() + timedelta(days=invitation_days)
        
        invitation = UserInvitation.objects.create(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            invited_by=request.user,
            expires_at=expires_at,
            company_id=company_id if company_id else None,
            department_id=department_id if department_id else None,
            branch_id=branch_id if branch_id else None,
            assigned_apps=assigned_apps,
        )
        
        # Send invitation email
        if invitation.send_invitation_email():
            messages.success(
                request,
                f"✅ Invitation sent to {email}! They have {invitation_days} days to accept."
            )
            
            # Log activity
            log_activity(
                user=request.user,
                action='create',
                content_type='User Invitation',
                object_id=invitation.id,
                object_repr=str(invitation),
                description=f"Sent invitation to {email} for role {role}",
                changes={'email': email, 'role': role, 'expires': str(expires_at)},
                success=True,
                request=request
            )
        else:
            messages.error(request, "Invitation created but email failed to send. Please try again.")
        
        return redirect('accounts:manage_invitations')
    
    # GET request - show invitation form
    from organization.models import Company, Department, Branch
    from accounts.models import App
    
    context = {
        'roles': User.ROLE_CHOICES,
        'companies': Company.objects.all(),
        'departments': Department.objects.all(),
        'branches': Branch.objects.all(),
        'apps': App.objects.filter(is_active=True),
    }
    
    return render(request, 'accounts/send_invitation.html', context)


@login_required
@permission_required('accounts.view_user', raise_exception=True)
def manage_invitations(request):
    """
    View to manage all invitations (pending, accepted, expired).
    Allows admins to resend or revoke invitations.
    """
    invitations = UserInvitation.objects.select_related(
        'invited_by', 'user', 'company', 'department', 'branch'
    ).all()
    
    # Update expired invitations
    for inv in invitations:
        inv.is_valid()  # This auto-updates status if expired
    
    context = {
        'invitations': invitations,
        'pending_count': invitations.filter(status='pending').count(),
        'accepted_count': invitations.filter(status='accepted').count(),
        'expired_count': invitations.filter(status='expired').count(),
    }
    
    return render(request, 'accounts/manage_invitations.html', context)


@require_http_methods(["POST"])
@login_required
@permission_required('accounts.delete_user', raise_exception=True)
def revoke_invitation(request, invitation_id):
    """Revoke a pending invitation"""
    invitation = get_object_or_404(UserInvitation, id=invitation_id)
    
    if invitation.status == 'pending':
        invitation.status = 'revoked'
        invitation.save()
        
        log_activity(
            user=request.user,
            action='delete',
            content_type='User Invitation',
            object_id=invitation.id,
            object_repr=str(invitation),
            description=f"Revoked invitation to {invitation.email}",
            success=True,
            request=request
        )
        
        messages.success(request, f"Invitation to {invitation.email} has been revoked")
    else:
        messages.error(request, "Can only revoke pending invitations")
    
    return redirect('accounts:manage_invitations')


@require_http_methods(["POST"])
@login_required
@permission_required('accounts.add_user', raise_exception=True)
def resend_invitation(request, invitation_id):
    """Resend an invitation email"""
    invitation = get_object_or_404(UserInvitation, id=invitation_id)
    
    if invitation.status == 'pending' and invitation.is_valid():
        if invitation.send_invitation_email():
            messages.success(request, f"Invitation resent to {invitation.email}")
        else:
            messages.error(request, "Failed to send email. Please try again.")
    else:
        messages.error(request, "Can only resend valid pending invitations")
    
    return redirect('accounts:manage_invitations')


def signup(request, token):
    """
    Signup view - users click invitation link to create account.
    Device is automatically whitelisted during signup.
    """
    invitation = get_object_or_404(UserInvitation, token=token)
    
    # Check organization settings
    require_email_verification = get_setting('REQUIRE_EMAIL_VERIFICATION', True)
    allow_self_registration = get_setting('ALLOW_USER_SELF_REGISTRATION', False)
    
    # Check if invitation is valid
    if not invitation.is_valid():
        context = {
            'error': 'expired',
            'invitation': invitation
        }
        return render(request, 'accounts/signup_error.html', context)
    
    # Check if invitation already accepted
    if invitation.status == 'accepted':
        messages.info(request, "This invitation has already been used.")
        return redirect('accounts:login')
    
    if request.method == 'POST':
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        # Auto-generate username in format: FirstInitial.LastName (e.g., A.Cheloti)
        first_name = invitation.first_name.strip()
        last_name = invitation.last_name.strip()
        
        # Get first initial and full last name
        first_initial = first_name[0].upper() if first_name else 'U'
        clean_last_name = last_name.replace(' ', '').replace('-', '').replace("'", '')
        base_username = f"{first_initial}.{clean_last_name}"
        
        # Ensure unique username by adding number suffix if needed
        username = base_username
        counter = 1
        while User.objects.filter(username__iexact=username).exists():
            username = f"{first_initial}.{clean_last_name}{counter}"
            counter += 1
        
        # Validate password
        if password != password_confirm:
            messages.error(request, "Passwords don't match!")
            return render(request, 'accounts/signup.html', {'invitation': invitation})
        
        # Check password requirements
        min_length = int(get_setting('MIN_PASSWORD_LENGTH', '12'))
        if len(password) < min_length:
            messages.error(request, f"Password must be at least {min_length} characters long")
            return render(request, 'accounts/signup.html', {'invitation': invitation})
        
        require_complexity = get_setting('REQUIRE_PASSWORD_COMPLEXITY', 'true')
        if require_complexity == 'true':
            if not (any(c.isupper() for c in password) and 
                    any(c.islower() for c in password) and 
                    any(c.isdigit() for c in password)):
                messages.error(
                    request, 
                    "Password must contain uppercase, lowercase, and numbers"
                )
                return render(request, 'accounts/signup.html', {'invitation': invitation})
        
        # Create user account
        try:
            user = User.objects.create_user(
                username=username,
                email=invitation.email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=invitation.role,
                company=invitation.company,
                department=invitation.department,
                branch=invitation.branch,
            )
            
            # Assign apps
            if invitation.assigned_apps:
                from accounts.models import App
                apps = App.objects.filter(name__in=invitation.assigned_apps)
                user.assigned_apps.set(apps)
            
            # Get device info
            device_info = get_device_info(request)
            ip_address = get_client_ip(request)
            location = get_location(ip_address)
            
            # Whitelist device automatically
            device = WhitelistedDevice.objects.create(
                user=user,
                device_name=device_info['device_name'],
                user_agent=device_info['user_agent'],
                ip_address=ip_address,
                location=location,
                is_primary=True,  # First device is primary
                registration_method='signup'
            )
            
            # Update invitation status
            invitation.status = 'accepted'
            invitation.accepted_at = timezone.now()
            invitation.user = user
            invitation.save()
            
            # Check email verification requirement
            if require_email_verification:
                # Mark user as inactive until email verified
                user.is_active = False
                user.save()
                
                # Generate verification token
                import uuid
                verification_token = str(uuid.uuid4())
                user.email_verification_token = verification_token
                user.save()
                
                # Send verification email
                verification_url = request.build_absolute_uri(
                    f"/accounts/verify-email/{verification_token}/"
                )
                
                subject = get_setting('EMAIL_SUBJECT_PREFIX', '[Petty Cash System]') + " Verify Your Email Address"
                message = f"""
Hello {user.get_display_name()},

Welcome to Petty Cash System! Please verify your email address by clicking the link below:

{verification_url}

This link will expire in 24 hours.

If you did not create this account, please ignore this email.

Best regards,
Petty Cash System Team
                """
                
                try:
                    from django.core.mail import send_mail
                    send_mail(
                        subject,
                        message,
                        get_setting('SYSTEM_EMAIL_FROM', settings.DEFAULT_FROM_EMAIL),
                        [user.email],
                        fail_silently=False,
                    )
                    
                    messages.success(
                        request,
                        "✅ Account created successfully! Please check your email and click the verification link to activate your account."
                    )
                    
                    return redirect('accounts:login')
                    
                except Exception as e:
                    # If email fails, activate account anyway to avoid blocking user
                    user.is_active = True
                    user.save()
                    messages.warning(
                        request,
                        "Account created but email verification failed. Please contact administrator."
                    )
            
            # Auto-login user (if email verification not required)
            login(request, user)
            
            messages.success(
                request,
                f"✅ Welcome {user.get_display_name()}! Your account has been created and this device has been whitelisted."
            )
            
            return redirect('accounts:dashboard')
            
        except Exception as e:
            messages.error(request, f"Error creating account: {str(e)}")
            return render(request, 'accounts/signup.html', {'invitation': invitation})
    
    # GET request - show signup form
    context = {
        'invitation': invitation,
        'min_password_length': get_setting('MIN_PASSWORD_LENGTH', '12'),
        'require_complexity': get_setting('REQUIRE_PASSWORD_COMPLEXITY', 'true'),
    }
    
    return render(request, 'accounts/signup.html', context)


def verify_email(request, token):
    """
    Email verification view for new user accounts.
    """
    user = get_object_or_404(User, email_verification_token=token)
    
    if user.is_active:
        messages.info(request, "Your email is already verified.")
        return redirect('accounts:login')
    
    # Check if token is expired (24 hours)
    if user.date_joined and (timezone.now() - user.date_joined) > timedelta(hours=24):
        messages.error(request, "Verification link has expired. Please contact administrator.")
        return redirect('accounts:login')
    
    # Activate user
    user.is_active = True
    user.email_verification_token = None
    user.save()
    
    # Log activity
    log_activity(
        user=user,
        action='verify_email',
        content_type='User Account',
        object_id=user.id,
        object_repr=str(user),
        description=f"Email verified for user: {user.username}",
        success=True,
        request=request
    )
    
    messages.success(request, "✅ Email verified successfully! You can now log in to your account.")
    return redirect('accounts:login')


@login_required
def my_devices(request):
    """
    User view to see their whitelisted devices.
    Can deactivate devices (except primary).
    """
    devices = WhitelistedDevice.objects.filter(user=request.user)
    
    context = {
        'devices': devices,
        'active_count': devices.filter(is_active=True).count(),
    }
    
    return render(request, 'accounts/my_devices.html', context)


@require_http_methods(["POST"])
@login_required
def deactivate_device(request, device_id):
    """User can deactivate their own non-primary devices"""
    device = get_object_or_404(WhitelistedDevice, id=device_id, user=request.user)
    
    if device.is_primary:
        messages.error(request, "Cannot deactivate primary device! Set another device as primary first.")
    else:
        device.deactivate()
        messages.success(request, f"Device '{device.device_name}' has been deactivated")
        
        log_activity(
            user=request.user,
            action='update',
            content_type='Whitelisted Device',
            object_id=device.id,
            object_repr=str(device),
            description=f"Deactivated device: {device.device_name}",
            success=True,
            request=request
        )
    
    return redirect('accounts:my_devices')


@require_http_methods(["POST"])
@login_required
def set_primary_device(request, device_id):
    """Set a device as primary"""
    device = get_object_or_404(WhitelistedDevice, id=device_id, user=request.user)
    
    if device.is_active:
        device.set_as_primary()
        messages.success(request, f"'{device.device_name}' is now your primary device")
        
        log_activity(
            user=request.user,
            action='update',
            content_type='Whitelisted Device',
            object_id=device.id,
            object_repr=str(device),
            description=f"Set primary device: {device.device_name}",
            success=True,
            request=request
        )
    else:
        messages.error(request, "Cannot set inactive device as primary")
    
    return redirect('accounts:my_devices')


@login_required
@permission_required('accounts.view_user', raise_exception=True)
def manage_user_devices(request, user_id):
    """
    Admin view to manage devices for a specific user.
    Can activate/deactivate devices.
    """
    user = get_object_or_404(User, id=user_id)
    devices = WhitelistedDevice.objects.filter(user=user)
    access_attempts = DeviceAccessAttempt.objects.filter(user=user)[:20]
    
    context = {
        'managed_user': user,
        'devices': devices,
        'access_attempts': access_attempts,
    }
    
    return render(request, 'accounts/manage_user_devices.html', context)


@require_http_methods(["POST"])
@login_required
@permission_required('accounts.change_user', raise_exception=True)
def admin_toggle_device(request, device_id):
    """Admin can activate/deactivate any user's device"""
    device = get_object_or_404(WhitelistedDevice, id=device_id)
    
    # Toggle active status
    device.is_active = not device.is_active
    device.save()
    
    action = "activated" if device.is_active else "deactivated"
    messages.success(request, f"Device '{device.device_name}' has been {action}")
    
    log_activity(
        user=request.user,
        action='update',
        content_type='Whitelisted Device',
        object_id=device.id,
        object_repr=str(device),
        description=f"Admin {action} device for {device.user.username}: {device.device_name}",
        changes={'is_active': device.is_active},
        success=True,
        request=request
    )
    
    return redirect('accounts:manage_user_devices', user_id=device.user.id)


@require_http_methods(["POST"])
@login_required
@permission_required('accounts.delete_user', raise_exception=True)
def admin_delete_device(request, device_id):
    """Admin can delete any user's device"""
    device = get_object_or_404(WhitelistedDevice, id=device_id)
    user_id = device.user.id
    device_name = device.device_name
    username = device.user.username
    
    # Check if it's the only device
    device_count = WhitelistedDevice.objects.filter(user=device.user).count()
    if device_count == 1:
        messages.error(request, "Cannot delete the only device. User must have at least one device.")
        return redirect('accounts:manage_user_devices', user_id=user_id)
    
    # Check if it's primary
    if device.is_primary:
        messages.error(request, "Cannot delete primary device. Set another device as primary first.")
        return redirect('accounts:manage_user_devices', user_id=user_id)
    
    # Delete device
    device.delete()
    
    messages.success(request, f"Device '{device_name}' has been permanently deleted")
    
    log_activity(
        user=request.user,
        action='delete',
        content_type='Whitelisted Device',
        object_id=device_id,
        object_repr=f"{username} - {device_name}",
        description=f"Admin deleted device for {username}: {device_name}",
        success=True,
        request=request
    )
    
    return redirect('accounts:manage_user_devices', user_id=user_id)


@require_http_methods(["POST"])
@login_required
@permission_required('accounts.change_user', raise_exception=True)
def admin_set_primary_device(request, device_id):
    """Admin can set any device as primary for a user"""
    device = get_object_or_404(WhitelistedDevice, id=device_id)
    
    if not device.is_active:
        messages.error(request, "Cannot set inactive device as primary. Activate it first.")
        return redirect('accounts:manage_user_devices', user_id=device.user.id)
    
    # Set as primary
    device.set_as_primary()
    
    messages.success(request, f"'{device.device_name}' is now the primary device")
    
    log_activity(
        user=request.user,
        action='update',
        content_type='Whitelisted Device',
        object_id=device.id,
        object_repr=str(device),
        description=f"Admin set primary device for {device.user.username}: {device.device_name}",
        changes={'is_primary': True},
        success=True,
        request=request
    )
    
    return redirect('accounts:manage_user_devices', user_id=device.user.id)


def device_blocked(request):
    """
    Page shown when user tries to access from non-whitelisted device.
    Allows them to request device registration.
    """
    context = {
        'support_email': get_setting('SECURITY_ALERT_RECIPIENTS', 'admin@company.com').split(',')[0],
    }
    return render(request, 'accounts/device_blocked.html', context)


def request_device_registration(request):
    """
    User can request their current device to be whitelisted.
    Sends email to admin with registration link.
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        reason = request.POST.get('reason', '')
        
        # Find user
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "No account found with that email address.")
            return render(request, 'accounts/request_device.html')
        
        # Get device info
        device_info = get_device_info(request)
        ip_address = get_client_ip(request)
        location = get_location(ip_address)
        
        # Check if device already exists
        existing_device = WhitelistedDevice.objects.filter(
            user=user,
            user_agent=device_info['user_agent']
        ).first()
        
        if existing_device:
            if existing_device.is_active:
                messages.info(request, "This device is already whitelisted. Please try logging in again.")
                return redirect('accounts:login')
            else:
                messages.info(request, "This device is registered but inactive. Please contact your administrator to activate it.")
                return render(request, 'accounts/request_device.html')
        
        # Create device registration request (inactive by default)
        device = WhitelistedDevice.objects.create(
            user=user,
            device_name=device_info['device_name'],
            user_agent=device_info['user_agent'],
            ip_address=ip_address,
            location=location,
            is_active=False,  # Requires admin approval
            is_primary=False,
            registration_method='self_service',
            notes=f"Self-service registration request. Reason: {reason}"
        )
        
        # Send email to admins
        admin_emails = get_setting('SECURITY_ALERT_RECIPIENTS', 'admin@company.com').split(',')
        admin_emails = [email.strip() for email in admin_emails if email.strip()]
        
        approval_url = f"{settings.SITE_URL}/accounts/users/{user.id}/devices/"
        
        subject = f"Device Registration Request - {user.get_display_name()}"
        message = f"""
A user has requested to register a new device:

User: {user.get_display_name()} ({user.username})
Email: {user.email}
Device: {device_info['device_name']}
IP Address: {ip_address}
Location: {location or 'Unknown'}
Reason: {reason or 'Not provided'}

To approve this device, visit:
{approval_url}

Then activate the device to allow access.

This is an automated security notification.
"""
        
        html_message = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6;">
    <h2 style="color: #e74c3c;">🔐 Device Registration Request</h2>
    
    <p>A user has requested to register a new device:</p>
    
    <table style="border-collapse: collapse; margin: 20px 0;">
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd; background-color: #f9f9f9;"><strong>User:</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">{user.get_display_name()} ({user.username})</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd; background-color: #f9f9f9;"><strong>Email:</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">{user.email}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd; background-color: #f9f9f9;"><strong>Device:</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">{device_info['device_name']}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd; background-color: #f9f9f9;"><strong>IP Address:</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;"><code>{ip_address}</code></td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd; background-color: #f9f9f9;"><strong>Location:</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">{location or 'Unknown'}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd; background-color: #f9f9f9;"><strong>Reason:</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">{reason or 'Not provided'}</td>
        </tr>
    </table>
    
    <div style="margin: 30px 0;">
        <a href="{approval_url}" 
           style="background-color: #3498db; color: white; padding: 12px 24px; 
                  text-decoration: none; border-radius: 5px; display: inline-block;">
            Review Device Request
        </a>
    </div>
    
    <p><small style="color: #7f8c8d;">To approve, click the link above and activate the device.</small></p>
    
    <hr style="border: none; border-top: 1px solid #ecf0f1; margin: 20px 0;">
    <p style="color: #95a5a6; font-size: 12px;">This is an automated security notification from {settings.SITE_NAME}.</p>
</body>
</html>
"""
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=admin_emails,
                html_message=html_message,
                fail_silently=False,
            )
            
            # Log the request
            log_activity(
                user=user,
                action='create',
                content_type='Device Registration Request',
                object_id=device.id,
                object_repr=str(device),
                description=f"User requested device registration: {device_info['device_name']}",
                changes={'device': device_info['device_name'], 'ip': ip_address, 'location': location},
                success=True,
                request=request
            )
            
            messages.success(
                request,
                "✅ Device registration request sent! An administrator will review your request shortly. "
                "You will be able to login once your device is approved."
            )
            return redirect('accounts:login')
            
        except Exception as e:
            messages.error(request, f"Error sending request: {str(e)}")
            device.delete()  # Clean up if email fails
            return render(request, 'accounts/request_device.html')
    
    # GET request
    return render(request, 'accounts/request_device.html')

