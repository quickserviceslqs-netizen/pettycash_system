"""
Admin Dashboard Views
User-friendly interface for managing users, permissions, and app access
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse
from accounts.models import User, App
from organization.models import Company, Branch, Department


@login_required
@permission_required('accounts.change_user', raise_exception=True)
def admin_dashboard(request):
    """Main admin dashboard for user and permission management"""
    
    # User statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    staff_users = User.objects.filter(is_staff=True).count()
    
    # Users by role
    users_by_role = User.objects.values('role').annotate(count=Count('id')).order_by('-count')
    
    # Users by company
    users_by_company = User.objects.filter(company__isnull=False).values(
        'company__name'
    ).annotate(count=Count('id')).order_by('-count')[:5]
    
    # App statistics
    apps = App.objects.filter(is_active=True)
    app_stats = []
    for app in apps:
        app_stats.append({
            'name': app.display_name,
            'user_count': app.users.count(),
            'is_active': app.is_active
        })
    
    # Recent users (last 10)
    recent_users = User.objects.order_by('-date_joined')[:10]
    
    context = {
        'total_users': total_users,
        'active_users': active_users,
        'staff_users': staff_users,
        'users_by_role': users_by_role,
        'users_by_company': users_by_company,
        'app_stats': app_stats,
        'recent_users': recent_users,
    }
    
    return render(request, 'accounts/admin_dashboard.html', context)


@login_required
@permission_required('accounts.change_user', raise_exception=True)
def manage_users(request):
    """User management page with search and filters"""
    
    # Get filter parameters
    role_filter = request.GET.get('role', '')
    company_filter = request.GET.get('company', '')
    status_filter = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    # Base queryset
    users = User.objects.select_related(
        'company', 'branch', 'department'
    ).prefetch_related('assigned_apps')
    
    # Apply filters
    if role_filter:
        users = users.filter(role=role_filter)
    if company_filter:
        users = users.filter(company_id=company_filter)
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    # Order by username
    users = users.order_by('username')
    
    # Get filter options
    companies = Company.objects.all().order_by('name')
    roles = User.ROLE_CHOICES
    
    context = {
        'users': users,
        'companies': companies,
        'roles': roles,
        'role_filter': role_filter,
        'company_filter': company_filter,
        'status_filter': status_filter,
        'search': search,
    }
    
    return render(request, 'accounts/manage_users.html', context)


@login_required
@permission_required('accounts.change_user', raise_exception=True)
def edit_user_permissions(request, user_id):
    """Edit user's app access and role"""
    
    user_to_edit = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Update role
        new_role = request.POST.get('role')
        if new_role in dict(User.ROLE_CHOICES):
            user_to_edit.role = new_role
        
        # Update app access
        app_ids = request.POST.getlist('apps')
        apps = App.objects.filter(id__in=app_ids, is_active=True)
        user_to_edit.assigned_apps.set(apps)
        
        # Update organization
        company_id = request.POST.get('company')
        branch_id = request.POST.get('branch')
        department_id = request.POST.get('department')
        
        if company_id:
            user_to_edit.company_id = company_id or None
        if branch_id:
            user_to_edit.branch_id = branch_id or None
        if department_id:
            user_to_edit.department_id = department_id or None
        
        # Update centralized approver
        user_to_edit.is_centralized_approver = request.POST.get('is_centralized_approver') == 'on'
        
        # Update active status
        user_to_edit.is_active = request.POST.get('is_active') == 'on'
        
        user_to_edit.save()
        
        messages.success(request, f'User {user_to_edit.username} updated successfully!')
        return redirect('accounts:manage_users')
    
    # GET request - show form
    all_apps = App.objects.filter(is_active=True)
    user_apps = user_to_edit.assigned_apps.all()
    companies = Company.objects.all().order_by('name')
    branches = Branch.objects.all().order_by('name')
    departments = Department.objects.all().order_by('name')
    
    context = {
        'user_to_edit': user_to_edit,
        'all_apps': all_apps,
        'user_apps': user_apps,
        'companies': companies,
        'branches': branches,
        'departments': departments,
        'roles': User.ROLE_CHOICES,
    }
    
    return render(request, 'accounts/edit_user_permissions.html', context)


@login_required
@permission_required('accounts.change_user', raise_exception=True)
def toggle_user_status(request, user_id):
    """Quick toggle for user active status"""
    
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        user.is_active = not user.is_active
        user.save()
        
        status = "activated" if user.is_active else "deactivated"
        messages.success(request, f'User {user.username} {status} successfully!')
    
    return redirect('accounts:manage_users')


@login_required
@permission_required('accounts.change_user', raise_exception=True)
def bulk_assign_app(request):
    """Bulk assign app to multiple users"""
    
    if request.method == 'POST':
        user_ids = request.POST.getlist('user_ids')
        app_id = request.POST.get('app_id')
        
        if user_ids and app_id:
            app = get_object_or_404(App, id=app_id)
            users = User.objects.filter(id__in=user_ids)
            
            for user in users:
                user.assigned_apps.add(app)
            
            messages.success(
                request, 
                f'App "{app.display_name}" assigned to {users.count()} user(s)!'
            )
        else:
            messages.error(request, 'Please select users and an app.')
    
    return redirect('accounts:manage_users')
