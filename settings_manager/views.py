from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from datetime import timedelta
import csv

from settings_manager.models import SystemSetting, ActivityLog, get_setting
from accounts.models import User, App
from organization.models import Company, Region, Branch, Department, CostCenter, Position


def is_admin_user(user):
    """Check if user is superuser or has admin role"""
    return user.is_superuser or user.role == 'admin'


@login_required
@user_passes_test(is_admin_user)
def settings_dashboard(request):
    """Main settings management dashboard"""
    # Log activity
    log_activity(request.user, 'view', content_type='Settings Dashboard', 
                 description='Viewed settings dashboard', request=request)
    
    # Get all settings grouped by category
    categories = SystemSetting.CATEGORY_CHOICES
    settings_by_category = {}
    
    for category_key, category_name in categories:
        settings = SystemSetting.objects.filter(category=category_key, is_active=True)
        if settings.exists():
            settings_by_category[category_name] = settings
    
    # Get filter and search
    category_filter = request.GET.get('category')
    search_query = request.GET.get('search', '').strip()
    
    if category_filter:
        settings = SystemSetting.objects.filter(category=category_filter, is_active=True)
    else:
        settings = SystemSetting.objects.filter(is_active=True)
    
    # Apply search filter if provided
    if search_query:
        settings = settings.filter(
            Q(display_name__icontains=search_query) |
            Q(key__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    context = {
        'settings_by_category': settings_by_category,
        'all_settings': settings,
        'categories': categories,
        'selected_category': category_filter,
        'search_query': search_query,
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
                changes={'old_value': old_value, 'new_value': new_value},
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
def system_info(request):
    """Display system information and diagnostics"""
    import sys
    import platform
    from django import get_version as django_version
    from django.conf import settings as django_settings
    
    # Log activity
    log_activity(request.user, 'view', content_type='System Info', 
                 description='Viewed system information', request=request)
    
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
