from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from datetime import timedelta
import csv
import sys
import platform
from django import get_version as django_version
from django.core.paginator import Paginator
from django.conf import settings as django_settings
import locale
from django.utils import timezone as django_timezone

from settings_manager.models import SystemSetting, ActivityLog, get_setting
from accounts.models import User, App
from organization.models import Company, Region, Branch, Department, CostCenter, Position
from system_maintenance.models import MaintenanceMode


def is_admin_user(user):
    """Check if user is superuser or has admin role"""
    return user.is_superuser or user.role == 'admin'


def can_manage_maintenance(user):
    """Allow superusers, admin role, or users with explicit manage_maintenance permission"""
    try:
        return user.is_superuser or getattr(user, 'role', '') == 'admin' or user.has_perm('system_maintenance.manage_maintenance')
    except Exception:
        return False


@login_required
@user_passes_test(is_admin_user)
def settings_dashboard(request):
    """Main settings management dashboard"""
    # Log activity
    log_activity(request.user, 'view', content_type='Settings Dashboard', 
                 description='Viewed settings dashboard', request=request)
    
    # Get all settings grouped by category
    from django.conf import settings as django_settings
    categories = getattr(django_settings, 'SYSTEM_SETTING_CATEGORIES', SystemSetting.CATEGORY_CHOICES)
    settings_by_category = {}
    for category_key, category_name in categories:
        settings = SystemSetting.objects.filter(category=category_key)
        if settings.exists():
            settings_by_category[category_key] = settings

    # Get filter and search
    category_filter = request.GET.get('category')
    search_query = request.GET.get('search', '').strip()

    # Filter settings
    settings = SystemSetting.objects.all()
    if category_filter:
        settings = settings.filter(category=category_filter)
        # For security category, show only settings that need attention
        if category_filter == 'security':
            settings = settings.filter(
                Q(is_active=False) | 
                Q(setting_type='boolean', value__in=['false', 'False']) |
                Q(value__in=['', None])
            )
    if search_query:
        settings = settings.filter(
            Q(display_name__icontains=search_query) |
            Q(key__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Security status
    secure_settings = [
        getattr(django_settings, 'SECURE_SSL_REDIRECT', False),
        getattr(django_settings, 'SESSION_COOKIE_SECURE', False),
        getattr(django_settings, 'CSRF_COOKIE_SECURE', False),
        getattr(django_settings, 'SECURE_BROWSER_XSS_FILTER', False),
        getattr(django_settings, 'SECURE_CONTENT_TYPE_NOSNIFF', False),
        getattr(django_settings, 'X_FRAME_OPTIONS', None) == 'DENY',
    ]
    secure_status = all(secure_settings)
    # Pagination for the All Settings table (default 25 per page)
    try:
        per_page = int(request.GET.get('per_page', 25))
    except (TypeError, ValueError):
        per_page = 25
    if per_page not in (10, 25, 50, 100):
        per_page = 25

    paginator = Paginator(settings, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'settings_by_category': settings_by_category,
        'all_settings': page_obj,  # paginated page object used in template
        'categories': categories,
        'selected_category': category_filter,
        'search_query': search_query,
        'total_settings': SystemSetting.objects.filter(is_active=True).count(),
        'secure_status': secure_status,
        'per_page': per_page,
        'total_results': paginator.count,
        'page_obj': page_obj,
    }
    # Provide direct edit links for some critical settings when available
    try:
        currency_setting = SystemSetting.objects.filter(key='CURRENCY_CODE').first()
        maintenance_setting = SystemSetting.objects.filter(key='SYSTEM_MAINTENANCE_MODE').first()
        context['currency_setting_id'] = currency_setting.id if currency_setting else None
        context['maintenance_setting_id'] = maintenance_setting.id if maintenance_setting else None
    except Exception:
        context['currency_setting_id'] = None
        context['maintenance_setting_id'] = None
    # Expose maintenance mode value to template (use get_setting to respect typed value)
    try:
        context['system_maintenance_mode'] = get_setting('SYSTEM_MAINTENANCE_MODE', 'false')
    except Exception:
        context['system_maintenance_mode'] = False
    # Expose whether there's an active MaintenanceMode session (middleware uses this)
    try:
        context['maintenance_session_active'] = MaintenanceMode.is_maintenance_active()
        # also provide latest session object if needed in template
        latest = MaintenanceMode.objects.order_by('-activated_at').first()
        context['maintenance_latest'] = latest
    except Exception:
        context['maintenance_session_active'] = False
        context['maintenance_latest'] = None
    # debug prints removed to keep logs clean
    return render(request, 'settings_manager/dashboard.html', context)


@login_required
@user_passes_test(is_admin_user)
def edit_setting(request, setting_id):
    """Edit a system setting"""
    setting = get_object_or_404(SystemSetting, id=setting_id)
    
    if not setting.editable_by_admin:
        messages.error(request, "This setting cannot be edited through the UI.")
        return redirect('settings_manager:dashboard')
    
    if request.method == 'POST':
        old_value = setting.value
        old_active = setting.is_active
        new_value = request.POST.get('value')
        new_active = request.POST.get('is_active') == 'on'
        
        setting.value = new_value
        setting.is_active = new_active
        setting.last_modified_by = request.user
        
        try:
            setting.full_clean()
            setting.save()
            
            # Log the change
            changes = {}
            if old_value != new_value:
                changes['value'] = {'old': old_value, 'new': new_value}
            if old_active != new_active:
                changes['is_active'] = {'old': old_active, 'new': new_active}
            
            log_activity(
                request.user,
                'setting_change',
                'System Setting',
                object_id=setting.key,
                object_repr=setting.display_name,
                description=f"Updated setting '{setting.display_name}'",
                changes=changes,
                request=request
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
                error_message=str(e),
                request=request
            )
        
        # After saving, prefer to return the user to the edit page (so they remain on the specific setting)
        next_url = request.POST.get('next') or request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('settings_manager:edit_setting', setting_id=setting.id)
    
    context = {
        'setting': setting,
    }
    
    return render(request, 'settings_manager/edit_setting.html', context)


@login_required
@user_passes_test(is_admin_user)
def activity_logs(request):
    """View activity logs with filtering"""
    # Log this view
    log_activity(request.user, 'view', content_type='Activity Logs', 
                 description='Viewed activity logs', request=request)
    
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
def category_detail(request, category_key):
    """Dedicated page showing settings for a single category"""
    # Log activity
    log_activity(request.user, 'view', content_type=f'Category: {category_key}',
                 description=f'Viewed settings for category {category_key}', request=request)

    from django.conf import settings as django_settings
    categories = getattr(django_settings, 'SYSTEM_SETTING_CATEGORIES', SystemSetting.CATEGORY_CHOICES)
    # Resolve display name
    display_name = None
    for key, name in categories:
        if key == category_key:
            display_name = name
            break
    if not display_name:
        display_name = category_key.title()

    # Query settings for the category
    settings_qs = SystemSetting.objects.filter(category=category_key).order_by('display_name')

    # Optional search
    search_query = request.GET.get('search', '').strip()
    if search_query:
        settings_qs = settings_qs.filter(
            Q(display_name__icontains=search_query) |
            Q(key__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Paginate results (default 25 per page, overridable via ?per_page=)
    try:
        per_page = int(request.GET.get('per_page', 25))
    except (TypeError, ValueError):
        per_page = 25
    # clamp to reasonable options
    if per_page not in (10, 25, 50, 100):
        per_page = 25

    paginator = Paginator(settings_qs, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'category_key': category_key,
        'category_name': display_name,
        'settings_list': page_obj.object_list,
        'page_obj': page_obj,
        'search_query': search_query,
        'per_page': per_page,
    }

    # Build a compact page range for the template (show first, last, and up to 2 pages around current)
    total = paginator.num_pages
    current = page_obj.number
    page_numbers = []
    if total <= 9:
        page_numbers = list(paginator.page_range)
    else:
        page_numbers.append(1)
        left = current - 2
        right = current + 2
        if left > 2:
            page_numbers.append('gap')
        for n in range(max(left, 2), min(right, total - 1) + 1):
            page_numbers.append(n)
        if right < total - 1:
            page_numbers.append('gap')
        page_numbers.append(total)

    context['page_numbers'] = page_numbers

    return render(request, 'settings_manager/category_detail.html', context)


@login_required
@user_passes_test(can_manage_maintenance)
def maintenance_manage(request):
    """Full maintenance management page: shows setting, active sessions, history, and controls."""
    from system_maintenance.models import MaintenanceMode as MM
    # Log activity
    log_activity(request.user, 'view', content_type='Maintenance', description='Viewed maintenance management', request=request)

    # Get system setting for maintenance (if exists)
    maintenance_setting = SystemSetting.objects.filter(key='SYSTEM_MAINTENANCE_MODE').first()
    try:
        maintenance_setting_value = get_setting('SYSTEM_MAINTENANCE_MODE', False)
    except Exception:
        maintenance_setting_value = False

    # Get latest maintenance session (active or most recent)
    latest_session = MM.objects.order_by('-activated_at').first()
    active_session = MM.objects.filter(is_active=True).order_by('-activated_at').first()

    # Handle POST actions
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'toggle_setting' and maintenance_setting:
            new_state = request.POST.get('is_active') == 'on'
            old_state = maintenance_setting.is_active
            maintenance_setting.is_active = new_state
            maintenance_setting.value = 'true' if new_state else 'false'
            maintenance_setting.last_modified_by = request.user
            try:
                maintenance_setting.full_clean()
                maintenance_setting.save()
                log_activity(request.user, 'setting_change', 'System Setting', object_id=maintenance_setting.key,
                             object_repr=maintenance_setting.display_name,
                             description=f"Toggled SYSTEM_MAINTENANCE_MODE to {new_state}", request=request)
                messages.success(request, 'Maintenance setting updated successfully.')
            except Exception as e:
                messages.error(request, f'Error updating maintenance setting: {e}')

        elif action == 'create_session':
            reason = request.POST.get('reason', '').strip() or 'Manual maintenance'
            try:
                duration = int(request.POST.get('duration_minutes', 30))
            except (TypeError, ValueError):
                duration = 30

            # Deactivate existing active sessions
            for s in MM.objects.filter(is_active=True):
                s.deactivate(request.user, success=False, notes='Superseded by new session')

            session = MM.objects.create(
                is_active=True,
                activated_by=request.user,
                activated_at=timezone.now(),
                reason=reason,
                estimated_duration_minutes=duration,
                expected_completion=timezone.now() + timezone.timedelta(minutes=duration),
                notify_users=request.POST.get('notify_users') == 'on',
                custom_message=request.POST.get('custom_message', '').strip(),
            )
            messages.success(request, 'Maintenance session created and activated.')
            log_activity(request.user, 'create', 'MaintenanceMode', object_id=session.id, object_repr=str(session),
                         description='Created maintenance session', request=request)

        elif action == 'deactivate_session':
            sid = request.POST.get('session_id')
            try:
                session = MM.objects.get(id=int(sid))
                session.deactivate(request.user, success=True, notes=request.POST.get('notes', '').strip())
                messages.success(request, 'Maintenance session deactivated.')
                log_activity(request.user, 'deactivate', 'MaintenanceMode', object_id=session.id, object_repr=str(session),
                             description='Deactivated maintenance session', request=request)
            except Exception as e:
                messages.error(request, f'Error deactivating session: {e}')

        elif action == 'sync_to_session':
            # Sync behavior: if setting true -> create session if none active; if false -> deactivate active
            try:
                setting_val = get_setting('SYSTEM_MAINTENANCE_MODE', False)
            except Exception:
                setting_val = False

            if setting_val:
                if not MM.objects.filter(is_active=True).exists():
                    s = MM.objects.create(
                        is_active=True,
                        activated_by=request.user,
                        activated_at=timezone.now(),
                        reason='Synced from SYSTEM_MAINTENANCE_MODE',
                        estimated_duration_minutes=30,
                        expected_completion=timezone.now() + timezone.timedelta(minutes=30),
                    )
                    messages.success(request, 'Created maintenance session to match setting.')
                    log_activity(request.user, 'create', 'MaintenanceMode', object_id=s.id, object_repr=str(s), description='Synced setting to session', request=request)
                else:
                    messages.info(request, 'An active maintenance session already exists.')
            else:
                for s in MM.objects.filter(is_active=True):
                    s.deactivate(request.user, success=True, notes='Synced from setting (disabled)')
                messages.success(request, 'Deactivated active maintenance sessions to match setting.')

        return redirect('settings_manager:maintenance')

    # Prepare history list (last 20)
    history = MM.objects.order_by('-activated_at')[:20]

    context = {
        'maintenance_setting': maintenance_setting,
        'maintenance_setting_value': maintenance_setting_value,
        'latest_session': latest_session,
        'active_session': active_session,
        'history': history,
    }

    return render(request, 'settings_manager/maintenance_manage.html', context)

@login_required
def system_info(request):
    from django.conf import settings as django_settings
    # Security status
    secure_settings = [
        getattr(django_settings, 'SECURE_SSL_REDIRECT', False),
        getattr(django_settings, 'SESSION_COOKIE_SECURE', False),
        getattr(django_settings, 'CSRF_COOKIE_SECURE', False),
        getattr(django_settings, 'SECURE_BROWSER_XSS_FILTER', False),
        getattr(django_settings, 'SECURE_CONTENT_TYPE_NOSNIFF', False),
        getattr(django_settings, 'X_FRAME_OPTIONS', None) == 'DENY',
    ]
    secure_status = all(secure_settings)
    import sys
    import platform
    import os
    import time
    from django import get_version as django_version
    from django.db import connection
    import locale
    from django.utils import timezone as django_timezone
    # Project name
    project_name = os.path.basename(str(django_settings.BASE_DIR)) if hasattr(django_settings, 'BASE_DIR') else 'N/A'
    # Server time
    server_time = django_timezone.now() if django_timezone else 'N/A'
    # Database name/host
    db_settings = django_settings.DATABASES.get('default', {})
    db_name = db_settings.get('NAME') or 'N/A'
    db_host = db_settings.get('HOST') or 'N/A'
    # Recent migrations
    migrations_error = None
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT app, name, applied FROM django_migrations ORDER BY applied DESC LIMIT 5;")
            recent_migrations = cursor.fetchall()
    except Exception as e:
        recent_migrations = []
        migrations_error = str(e)
    # Storage usage (disk/database size)
    db_size = None
    try:
        if 'postgres' in db_settings.get('ENGINE', ''):
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_database_size(current_database());")
                db_size = cursor.fetchone()[0]
        elif 'sqlite' in db_settings.get('ENGINE', ''):
            db_path = db_settings.get('NAME', '')
            if db_path and os.path.exists(db_path):
                db_size = os.path.getsize(db_path)
    except Exception:
        db_size = None
    if db_size is None:
        db_size = 'N/A'
    # Uptime
    uptime_error = None
    try:
        if hasattr(django_settings, 'SERVER_START_TIME'):
            uptime_seconds = int(time.time() - django_settings.SERVER_START_TIME)
        else:
            uptime_seconds = 'N/A'
            uptime_error = 'SERVER_START_TIME not set in settings.'
    except Exception as e:
        uptime_seconds = 'N/A'
        uptime_error = str(e)
    # Environment
    environment_error = None
    environment = os.environ.get('DJANGO_ENV')
    if not environment:
        # Fallback: infer from DEBUG and database host
        if django_settings.DEBUG:
            environment = 'development'
        elif db_host and ('render' in db_host or 'railway' in db_host or 'supabase' in db_host):
            environment = 'production'
        else:
            environment = 'staging'
        environment_error = 'DJANGO_ENV environment variable not set. Value inferred.'
    # Warnings/errors
    warnings = []
    errors = []
    # Statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    total_settings = SystemSetting.objects.filter(is_active=True).count()
    total_logs = ActivityLog.objects.count()
    context = {
        'project_name': project_name,
        'server_time': server_time,
        'python_version': sys.version if sys.version else 'N/A',
        'python_implementation': platform.python_implementation() if platform.python_implementation() else 'N/A',
        'python_executable': sys.executable if sys.executable else 'N/A',
        'django_version': django_version() if django_version else 'N/A',
        'debug_mode': django_settings.DEBUG,
        'database_engine': db_settings.get('ENGINE', 'N/A'),
        'database_name': db_name,
        'database_host': db_host,
        'recent_migrations': recent_migrations,
        'migrations_error': migrations_error,
        'db_size': db_size,
        'uptime_seconds': uptime_seconds,
        'uptime_error': uptime_error,
        'timezone': str(django_settings.TIME_ZONE) if hasattr(django_settings, 'TIME_ZONE') else 'N/A',
        'language': locale.getdefaultlocale()[0] if locale.getdefaultlocale() and locale.getdefaultlocale()[0] else 'N/A',
        'platform_system': platform.system() if platform.system() else 'N/A',
        'platform_release': platform.release() if platform.release() else 'N/A',
        'platform_machine': platform.architecture()[0] if platform.architecture() else 'N/A',
        'platform_processor': platform.processor() if platform.processor() else 'N/A',
        'installed_apps': django_settings.INSTALLED_APPS if hasattr(django_settings, 'INSTALLED_APPS') else [],
        'middleware': django_settings.MIDDLEWARE if hasattr(django_settings, 'MIDDLEWARE') else [],
        'secret_key': django_settings.SECRET_KEY if hasattr(django_settings, 'SECRET_KEY') else 'N/A',
        'environment': environment,
        'environment_error': environment_error,
        'warnings': warnings,
        'errors': errors,
        'total_users': total_users,
        'active_users': active_users,
        'total_settings': total_settings,
        'total_logs': total_logs,
        'secure_status': secure_status,
    }
    return render(request, 'settings_manager/system_info.html', context)


def log_activity(user, action, content_type='', object_id='', object_repr='', 
                 description='', changes=None, success=True, error_message='', request=None):
    """
    Helper function to log admin activities.
    Can be called from anywhere in the application.
    Captures IP address, device name, location, and user agent.
    """
    ip_address = None
    device_name = ''
    location = ''
    user_agent = ''
    
    if request:
        # Get IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        # Get location from IP address
        if ip_address and ip_address not in ['127.0.0.1', 'localhost', '::1']:
            # Check if geolocation is enabled in settings
            from settings_manager.models import get_setting
            if get_setting('ENABLE_ACTIVITY_GEOLOCATION', 'true') == 'true':
                try:
                    import requests
                    # Use a free IP geolocation API
                    response = requests.get(
                        f'http://ip-api.com/json/{ip_address}',
                        timeout=2  # 2 second timeout
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('status') == 'success':
                            city = data.get('city', '')
                            region = data.get('regionName', '')
                            country = data.get('country', '')
                            
                            # Build location string
                            location_parts = []
                            if city:
                                location_parts.append(city)
                            if region and region != city:
                                location_parts.append(region)
                            if country:
                                location_parts.append(country)
                            
                            location = ', '.join(location_parts)
                except Exception:
                    # If geolocation fails, continue without location
                    pass
        
        # For local development
        if not location and ip_address in ['127.0.0.1', 'localhost', '::1']:
            location = 'Local Development'
        
        # Get device name from hostname (if available in headers)
        device_name = request.META.get('REMOTE_HOST', '')
        
        # If REMOTE_HOST not available, try to get from user agent
        if not device_name:
            user_agent_str = request.META.get('HTTP_USER_AGENT', '')
            # Extract device info from user agent string
            if user_agent_str:
                # Try to parse device name from user agent
                import re
                # Look for patterns like "Windows NT 10.0", "Macintosh", "Linux", etc.
                if 'Windows' in user_agent_str:
                    match = re.search(r'Windows NT ([\d.]+)', user_agent_str)
                    if match:
                        version = match.group(1)
                        version_map = {
                            '10.0': 'Windows 10/11',
                            '6.3': 'Windows 8.1',
                            '6.2': 'Windows 8',
                            '6.1': 'Windows 7',
                        }
                        device_name = version_map.get(version, f'Windows NT {version}')
                elif 'Macintosh' in user_agent_str or 'Mac OS X' in user_agent_str:
                    match = re.search(r'Mac OS X ([\d_]+)', user_agent_str)
                    if match:
                        device_name = f"macOS {match.group(1).replace('_', '.')}"
                    else:
                        device_name = 'macOS'
                elif 'Linux' in user_agent_str:
                    if 'Android' in user_agent_str:
                        match = re.search(r'Android ([\d.]+)', user_agent_str)
                        if match:
                            device_name = f"Android {match.group(1)}"
                        else:
                            device_name = 'Android'
                    else:
                        device_name = 'Linux'
                elif 'iPhone' in user_agent_str or 'iPad' in user_agent_str:
                    match = re.search(r'OS ([\d_]+)', user_agent_str)
                    if match:
                        device_name = f"iOS {match.group(1).replace('_', '.')}"
                    else:
                        device_name = 'iOS'
                
                # Also try to get browser info
                if 'Chrome/' in user_agent_str and 'Edg/' not in user_agent_str:
                    device_name += ' - Chrome' if device_name else 'Chrome'
                elif 'Edg/' in user_agent_str or 'Edge/' in user_agent_str:
                    device_name += ' - Edge' if device_name else 'Edge'
                elif 'Firefox/' in user_agent_str:
                    device_name += ' - Firefox' if device_name else 'Firefox'
                elif 'Safari/' in user_agent_str and 'Chrome' not in user_agent_str:
                    device_name += ' - Safari' if device_name else 'Safari'
        
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
        device_name=device_name[:255] if device_name else '',
        location=location[:255] if location else '',
        user_agent=user_agent[:500] if user_agent else '',
        changes=changes,
        success=success,
        error_message=error_message
    )


# ==================== DATA OPERATIONS VIEWS ====================

@login_required
@user_passes_test(is_admin_user)
def data_operations_dashboard(request):
    """Main data operations dashboard"""
    # Get statistics
    stats = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'inactive_users': User.objects.filter(is_active=False).count(),
        'total_departments': Department.objects.count(),
        'total_branches': Branch.objects.count(),
        'total_regions': Region.objects.count(),
        'total_companies': Company.objects.count(),
        'users_by_role': dict(User.objects.values('role').annotate(count=Count('role'))),
    }
    
    log_activity(request.user, 'view', 'Data Operations Dashboard', description='Viewed data operations dashboard')
    
    context = {'stats': stats}
    return render(request, 'settings_manager/data_operations_dashboard.html', context)


@login_required
@user_passes_test(is_admin_user)
def manage_users(request):
    """User management interface"""
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    
    users = User.objects.all().select_related('department').order_by('-date_joined')
    
    if search_query:
        users = users.filter(
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    if role_filter:
        users = users.filter(role=role_filter)
    
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    context = {
        'users': users,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'roles': User.ROLE_CHOICES,
    }
    
    return render(request, 'settings_manager/manage_users.html', context)


@login_required
@user_passes_test(is_admin_user)
def create_user(request):
    """Create new user"""
    if request.method == 'POST':
        try:
            email = request.POST.get('email')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            role = request.POST.get('role')
            department_id = request.POST.get('department')
            password = request.POST.get('password')
            
            # Check if user exists
            if User.objects.filter(email=email).exists():
                messages.error(request, f'User with email {email} already exists.')
                return redirect('settings_manager:create_user')
            
            # Create user
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role
            )
            
            if department_id:
                user.department_id = department_id
                user.save()
            
            log_activity(request.user, 'create', content_type='User', object_id=user.id,
                        object_repr=str(user), description=f'Created user: {user.email}',
                        changes={'email': user.email, 'role': user.role, 'department': str(user.department) if user.department else None},
                        request=request)
            messages.success(request, f'User {user.email} created successfully.')
            return redirect('settings_manager:manage_users')
            
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
            log_activity(request.user, 'create', content_type='User',
                        description=f'Failed to create user', success=False, 
                        error_message=str(e), request=request)
    
    context = {
        'departments': Department.objects.all().select_related('branch'),
        'roles': User.ROLE_CHOICES,
    }
    return render(request, 'settings_manager/create_user.html', context)


@login_required
@user_passes_test(is_admin_user)
def edit_user(request, user_id):
    """Edit existing user"""
    user_obj = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        try:
            user_obj.first_name = request.POST.get('first_name')
            user_obj.last_name = request.POST.get('last_name')
            user_obj.role = request.POST.get('role')
            user_obj.is_active = request.POST.get('is_active') == 'on'
            
            department_id = request.POST.get('department')
            if department_id:
                user_obj.department_id = department_id
            
            user_obj.save()
            
            old_values = {k: request.POST.get(f'old_{k}', '') for k in ['email', 'first_name', 'last_name', 'role']}
            new_values = {'email': user_obj.email, 'first_name': user_obj.first_name, 
                         'last_name': user_obj.last_name, 'role': user_obj.role}
            
            log_activity(request.user, 'update', content_type='User', object_id=user_obj.id,
                        object_repr=str(user_obj), description=f'Updated user: {user_obj.email}',
                        changes={'before': old_values, 'after': new_values}, request=request)
            messages.success(request, f'User {user_obj.email} updated successfully.')
            return redirect('settings_manager:manage_users')
            
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
            log_activity(request.user, 'update', content_type='User', object_id=user_obj.id,
                        description=f'Failed to update user {user_obj.email}', 
                        success=False, error_message=str(e), request=request)
    
    context = {
        'user_obj': user_obj,
        'departments': Department.objects.all().select_related('branch'),
        'roles': User.ROLE_CHOICES,
    }
    return render(request, 'settings_manager/edit_user.html', context)


@login_required
@user_passes_test(is_admin_user)
def toggle_user_status(request, user_id):
    """Activate/Deactivate user"""
    user_obj = get_object_or_404(User, id=user_id)
    user_obj.is_active = not user_obj.is_active
    user_obj.save()
    
    status = 'activated' if user_obj.is_active else 'deactivated'
    log_activity(request.user, 'update', content_type='User', object_id=user_obj.id,
                object_repr=str(user_obj), description=f'{status.capitalize()} user: {user_obj.email}',
                changes={'is_active': user_obj.is_active, 'status': status}, request=request)
    messages.success(request, f'User {user_obj.email} {status} successfully.')
    
    return redirect('settings_manager:manage_users')


@login_required
@user_passes_test(is_admin_user)
def manage_departments(request):
    """Department management interface"""
    search_query = request.GET.get('search', '')
    branch_filter = request.GET.get('branch', '')
    
    departments = Department.objects.all().select_related('branch', 'branch__region').order_by('name')
    
    if search_query:
        departments = departments.filter(name__icontains=search_query)
    
    if branch_filter:
        departments = departments.filter(branch_id=branch_filter)
    
    context = {
        'departments': departments,
        'branches': Branch.objects.all().select_related('region'),
        'search_query': search_query,
        'branch_filter': branch_filter,
    }
    
    return render(request, 'settings_manager/manage_departments.html', context)


@login_required
@user_passes_test(is_admin_user)
def create_department(request):
    """Create new department"""
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            branch_id = request.POST.get('branch')
            
            department = Department.objects.create(
                name=name,
                branch_id=branch_id
            )
            
            log_activity(request.user, 'create', content_type='Department', object_id=department.id,
                        object_repr=str(department), description=f'Created department: {department.name}',
                        changes={'name': department.name, 'branch': str(department.branch)}, request=request)
            messages.success(request, f'Department {department.name} created successfully.')
            return redirect('settings_manager:manage_departments')
            
        except Exception as e:
            messages.error(request, f'Error creating department: {str(e)}')
            log_activity(request.user, 'create', content_type='Department',
                        description=f'Failed to create department', 
                        success=False, error_message=str(e), request=request)
    
    context = {
        'branches': Branch.objects.all().select_related('region'),
    }
    return render(request, 'settings_manager/create_department.html', context)


@login_required
@user_passes_test(is_admin_user)
def edit_department(request, department_id):
    """Edit existing department"""
    department = get_object_or_404(Department, id=department_id)
    
    if request.method == 'POST':
        try:
            old_name = department.name
            old_branch = department.branch
            
            department.name = request.POST.get('name')
            branch_id = request.POST.get('branch')
            if branch_id:
                department.branch_id = branch_id
            
            department.save()
            
            log_activity(request.user, 'update', content_type='Department', object_id=department.id,
                        object_repr=str(department), description=f'Updated department: {department.name}',
                        changes={'old_name': old_name, 'new_name': department.name, 
                                'old_branch': str(old_branch), 'new_branch': str(department.branch)}, 
                        request=request)
            messages.success(request, f'Department {department.name} updated successfully.')
            return redirect('settings_manager:manage_departments')
            
        except Exception as e:
            messages.error(request, f'Error updating department: {str(e)}')
            log_activity(request.user, 'update', content_type='Department', object_id=department.id,
                        description=f'Failed to update department', 
                        success=False, error_message=str(e), request=request)
    
    context = {
        'department': department,
        'branches': Branch.objects.all().select_related('region'),
    }
    return render(request, 'settings_manager/edit_department.html', context)


@login_required
@user_passes_test(is_admin_user)
def delete_department(request, department_id):
    """Delete department"""
    department = get_object_or_404(Department, id=department_id)
    
    if request.method == 'POST':
        name = department.name
        department.delete()
        
        log_activity(request.user, 'delete', content_type='Department',
                    description=f'Deleted department: {name}', request=request)
        messages.success(request, f'Department {name} deleted successfully.')
    
    return redirect('settings_manager:manage_departments')


@login_required
@user_passes_test(is_admin_user)
def manage_regions(request):
    """Region management interface"""
    regions = Region.objects.all().select_related('company').order_by('name')
    
    context = {
        'regions': regions,
        'companies': Company.objects.all(),
    }
    
    return render(request, 'settings_manager/manage_regions.html', context)


@login_required
@user_passes_test(is_admin_user)
def create_region(request):
    """Create new region"""
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            code = request.POST.get('code')
            company_id = request.POST.get('company')
            
            region = Region.objects.create(
                name=name,
                code=code,
                company_id=company_id
            )
            
            log_activity(request.user, 'create', content_type='Region', object_id=region.id,
                        object_repr=str(region), description=f'Created region: {region.name}',
                        changes={'name': region.name, 'code': region.code, 'company': str(region.company)}, 
                        request=request)
            messages.success(request, f'Region {region.name} created successfully.')
            return redirect('settings_manager:manage_regions')
            
        except Exception as e:
            messages.error(request, f'Error creating region: {str(e)}')
            log_activity(request.user, 'create', content_type='Region',
                        description=f'Failed to create region', 
                        success=False, error_message=str(e), request=request)
    
    context = {
        'companies': Company.objects.all(),
    }
    return render(request, 'settings_manager/create_region.html', context)


@login_required
@user_passes_test(is_admin_user)
def edit_region(request, region_id):
    """Edit existing region"""
    region = get_object_or_404(Region, id=region_id)
    
    if request.method == 'POST':
        try:
            old_name = region.name
            old_code = region.code
            old_company = region.company
            
            region.name = request.POST.get('name')
            region.code = request.POST.get('code')
            company_id = request.POST.get('company')
            if company_id:
                region.company_id = company_id
            
            region.save()
            
            log_activity(request.user, 'update', content_type='Region', object_id=region.id,
                        object_repr=str(region), description=f'Updated region: {region.name}',
                        changes={'old_name': old_name, 'new_name': region.name,
                                'old_code': old_code, 'new_code': region.code,
                                'old_company': str(old_company), 'new_company': str(region.company)}, 
                        request=request)
            messages.success(request, f'Region {region.name} updated successfully.')
            return redirect('settings_manager:manage_regions')
            
        except Exception as e:
            messages.error(request, f'Error updating region: {str(e)}')
            log_activity(request.user, 'update', content_type='Region', object_id=region.id,
                        description=f'Failed to update region', 
                        success=False, error_message=str(e), request=request)
    
    context = {
        'region': region,
        'companies': Company.objects.all(),
    }
    return render(request, 'settings_manager/edit_region.html', context)


@login_required
@user_passes_test(is_admin_user)
def delete_region(request, region_id):
    """Delete region"""
    region = get_object_or_404(Region, id=region_id)
    
    if request.method == 'POST':
        name = region.name
        region.delete()
        
        log_activity(request.user, 'delete', content_type='Region',
                    description=f'Deleted region: {name}', request=request)
        messages.success(request, f'Region {name} deleted successfully.')
    
    return redirect('settings_manager:manage_regions')


@login_required
@user_passes_test(is_admin_user)
def export_users_csv(request):
    """Export users to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Email', 'First Name', 'Last Name', 'Role', 'Department', 'Branch', 'Active', 'Date Joined'])
    
    users = User.objects.all().select_related('department', 'department__branch')
    for user in users:
        writer.writerow([
            user.email,
            user.first_name,
            user.last_name,
            user.get_role_display(),
            user.department.name if user.department else '',
            user.department.branch.name if user.department and user.department.branch else '',
            'Yes' if user.is_active else 'No',
            user.date_joined.strftime('%Y-%m-%d'),
        ])
    
    log_activity(request.user, 'export', content_type='User Data',
                description=f'Exported {users.count()} users to CSV',
                changes={'count': users.count(), 'format': 'CSV'}, request=request)
    return response
