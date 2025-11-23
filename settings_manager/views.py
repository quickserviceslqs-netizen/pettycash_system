from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta

from settings_manager.models import SystemSetting, ActivityLog, get_setting


def is_admin_user(user):
    """Check if user is superuser or has admin role"""
    return user.is_superuser or user.role == 'admin'


@login_required
@user_passes_test(is_admin_user)
def settings_dashboard(request):
    """Main settings management dashboard"""
    # Log activity
    log_activity(request.user, 'view', 'Settings Dashboard', description='Viewed settings dashboard')
    
    # Get all settings grouped by category
    categories = SystemSetting.CATEGORY_CHOICES
    settings_by_category = {}
    
    for category_key, category_name in categories:
        settings = SystemSetting.objects.filter(category=category_key, is_active=True)
        if settings.exists():
            settings_by_category[category_name] = settings
    
    # Get filter
    category_filter = request.GET.get('category')
    if category_filter:
        settings = SystemSetting.objects.filter(category=category_filter, is_active=True)
    else:
        settings = SystemSetting.objects.filter(is_active=True)
    
    context = {
        'settings_by_category': settings_by_category,
        'all_settings': settings,
        'categories': categories,
        'selected_category': category_filter,
        'total_settings': SystemSetting.objects.filter(is_active=True).count(),
    }
    
    return render(request, 'settings_manager/dashboard.html', context)


@login_required
@user_passes_test(is_admin_user)
def edit_setting(request, setting_id):
    """Edit a system setting"""
    setting = get_object_or_404(SystemSetting, id=setting_id)
    
    if not setting.editable_by_admin:
        messages.error(request, "This setting cannot be edited through the UI.")
        return redirect('settings-dashboard')
    
    if request.method == 'POST':
        old_value = setting.value
        new_value = request.POST.get('value')
        
        setting.value = new_value
        setting.last_modified_by = request.user
        
        try:
            setting.full_clean()
            setting.save()
            
            # Log the change
            log_activity(
                request.user,
                'setting_change',
                'System Setting',
                object_id=setting.key,
                object_repr=setting.display_name,
                description=f"Changed '{setting.display_name}' from '{old_value}' to '{new_value}'",
                changes={'old_value': old_value, 'new_value': new_value}
            )
            
            if setting.requires_restart:
                messages.warning(
                    request,
                    f"Setting updated successfully! NOTE: Server restart required for this change to take effect."
                )
            else:
                messages.success(request, f"Setting '{setting.display_name}' updated successfully!")
            
        except Exception as e:
            messages.error(request, f"Error updating setting: {str(e)}")
            log_activity(
                request.user,
                'setting_change',
                'System Setting',
                object_id=setting.key,
                success=False,
                error_message=str(e)
            )
        
        return redirect('settings-dashboard')
    
    context = {
        'setting': setting,
    }
    
    return render(request, 'settings_manager/edit_setting.html', context)


@login_required
@user_passes_test(is_admin_user)
def activity_logs(request):
    """View activity logs with filtering"""
    # Log this view
    log_activity(request.user, 'view', 'Activity Logs', description='Viewed activity logs')
    
    # Get filters
    action_filter = request.GET.get('action')
    user_filter = request.GET.get('user')
    days_filter = int(request.GET.get('days', 7))
    
    # Base queryset
    logs = ActivityLog.objects.select_related('user').all()
    
    # Apply filters
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    if user_filter:
        logs = logs.filter(user__username__icontains=user_filter)
    
    # Date filter
    if days_filter:
        start_date = timezone.now() - timedelta(days=days_filter)
        logs = logs.filter(timestamp__gte=start_date)
    
    # Paginate (last 100)
    logs = logs[:100]
    
    # Get statistics
    stats = ActivityLog.objects.filter(
        timestamp__gte=timezone.now() - timedelta(days=days_filter)
    ).aggregate(
        total=Count('id'),
        failed=Count('id', filter=Q(success=False))
    )
    
    # Get top users
    top_users = ActivityLog.objects.filter(
        timestamp__gte=timezone.now() - timedelta(days=days_filter)
    ).values('user__username').annotate(
        activity_count=Count('id')
    ).order_by('-activity_count')[:5]
    
    context = {
        'logs': logs,
        'actions': ActivityLog.ACTION_CHOICES,
        'selected_action': action_filter,
        'selected_user': user_filter,
        'days_filter': days_filter,
        'stats': stats,
        'top_users': top_users,
    }
    
    return render(request, 'settings_manager/activity_logs.html', context)


@login_required
@user_passes_test(is_admin_user)
def system_info(request):
    """Display system information and diagnostics"""
    import sys
    import platform
    from django import get_version as django_version
    from django.conf import settings as django_settings
    
    # Log activity
    log_activity(request.user, 'view', 'System Info', description='Viewed system information')
    
    context = {
        'python_version': sys.version,
        'django_version': django_version(),
        'platform': platform.platform(),
        'debug_mode': django_settings.DEBUG,
        'database_engine': django_settings.DATABASES['default']['ENGINE'],
        'installed_apps': django_settings.INSTALLED_APPS,
        'middleware': django_settings.MIDDLEWARE,
    }
    
    return render(request, 'settings_manager/system_info.html', context)


def log_activity(user, action, content_type='', object_id='', object_repr='', 
                 description='', changes=None, success=True, error_message='', request=None):
    """
    Helper function to log admin activities.
    Can be called from anywhere in the application.
    """
    ip_address = None
    user_agent = ''
    
    if request:
        # Get IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        # Get user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    ActivityLog.objects.create(
        user=user,
        action=action,
        content_type=content_type,
        object_id=str(object_id),
        object_repr=object_repr,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent[:255] if user_agent else '',
        changes=changes,
        success=success,
        error_message=error_message
    )
