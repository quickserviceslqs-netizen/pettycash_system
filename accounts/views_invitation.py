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
            return redirect('invite_user')
        
        # Check for pending invitations
        existing_pending = UserInvitation.objects.filter(
            email=email,
            status='pending'
        ).first()
        
        if existing_pending and existing_pending.is_valid():
            messages.warning(request, f"A pending invitation already exists for {email}")
            return redirect('invite_user')
        
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
        
        return redirect('manage_invitations')
    
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
    
    return redirect('manage_invitations')


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
    
    return redirect('manage_invitations')


def signup(request, token):
    """
    Signup view - users click invitation link to create account.
    Device is automatically whitelisted during signup.
    """
    invitation = get_object_or_404(UserInvitation, token=token)
    
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
        return redirect('login')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
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
        
        # Check username availability
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken!")
            return render(request, 'accounts/signup.html', {'invitation': invitation})
        
        # Create user account
        try:
            user = User.objects.create_user(
                username=username,
                email=invitation.email,
                password=password,
                first_name=invitation.first_name,
                last_name=invitation.last_name,
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
            
            # Log activity
            log_activity(
                user=user,
                action='create',
                content_type='User Account',
                object_id=user.id,
                object_repr=str(user),
                description=f"New user registered via invitation: {user.username}",
                changes={
                    'username': username,
                    'email': invitation.email,
                    'role': invitation.role,
                    'device_whitelisted': device_info['device_name'],
                    'ip': ip_address,
                    'location': location
                },
                success=True,
                request=request
            )
            
            # Auto-login user
            login(request, user)
            
            messages.success(
                request,
                f"✅ Welcome {user.get_display_name()}! Your account has been created and this device has been whitelisted."
            )
            
            return redirect('dashboard')
            
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
    
    return redirect('my_devices')


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
    
    return redirect('my_devices')


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
    
    return redirect('manage_user_devices', user_id=device.user.id)


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
        return redirect('manage_user_devices', user_id=user_id)
    
    # Check if it's primary
    if device.is_primary:
        messages.error(request, "Cannot delete primary device. Set another device as primary first.")
        return redirect('manage_user_devices', user_id=user_id)
    
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
    
    return redirect('manage_user_devices', user_id=user_id)


@require_http_methods(["POST"])
@login_required
@permission_required('accounts.change_user', raise_exception=True)
def admin_set_primary_device(request, device_id):
    """Admin can set any device as primary for a user"""
    device = get_object_or_404(WhitelistedDevice, id=device_id)
    
    if not device.is_active:
        messages.error(request, "Cannot set inactive device as primary. Activate it first.")
        return redirect('manage_user_devices', user_id=device.user.id)
    
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
    
    return redirect('manage_user_devices', user_id=device.user.id)
