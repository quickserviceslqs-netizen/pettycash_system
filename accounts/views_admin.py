"""
Admin Dashboard Views
User-friendly interface for managing users, permissions, and app access
Admin stats are integrated into the main dashboard (accounts/views.py)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.utils.crypto import get_random_string
from accounts.models import User, App
from organization.models import Company, Branch, Department


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
@permission_required('accounts.add_user', raise_exception=True)
def create_user(request):
    """Create a new user with details, apps, groups, and permissions"""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        role = request.POST.get('role')
        is_active = request.POST.get('is_active') == 'on'

        company_id = request.POST.get('company') or None
        branch_id = request.POST.get('branch') or None
        department_id = request.POST.get('department') or None

        if not username:
            messages.error(request, 'Username is required.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        else:
            temp_password = get_random_string(12)
            user = User.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=role if role in dict(User.ROLE_CHOICES) else User.REQUESTER,
                is_active=is_active,
                company_id=company_id,
                branch_id=branch_id,
                department_id=department_id,
            )
            user.set_password(temp_password)
            user.save()

            # Apps
            app_ids = request.POST.getlist('apps')
            if app_ids:
                apps = App.objects.filter(id__in=app_ids, is_active=True)
                user.assigned_apps.set(apps)

            # Groups
            group_ids = request.POST.getlist('groups')
            if group_ids:
                groups = Group.objects.filter(id__in=group_ids)
                user.groups.set(groups)

            # Permissions
            permission_ids = request.POST.getlist('permissions')
            if permission_ids:
                perms = Permission.objects.filter(id__in=permission_ids)
                user.user_permissions.set(perms)

            messages.success(
                request,
                f'User {username} created. Temporary password: {temp_password}'
            )
            return redirect('accounts:manage_users')

    # GET: show form
    companies = Company.objects.all().order_by('name')
    branches = Branch.objects.all().order_by('name')
    departments = Department.objects.all().order_by('name')
    all_apps = App.objects.filter(is_active=True)
    all_groups = Group.objects.all().order_by('name')

    content_types = ContentType.objects.filter(
        app_label__in=['transactions', 'workflow', 'treasury', 'reports', 'accounts', 'organization', 'settings_manager']
    ).order_by('app_label', 'model')

    permissions_by_app = {}
    for ct in content_types:
        app_label = ct.app_label
        permissions_by_app.setdefault(app_label, [])
        perms = Permission.objects.filter(content_type=ct).order_by('codename')
        for perm in perms:
            permissions_by_app[app_label].append({
                'id': perm.id,
                'name': perm.name,
                'codename': perm.codename,
                'model': ct.model,
            })

    context = {
        'companies': companies,
        'branches': branches,
        'departments': departments,
        'roles': User.ROLE_CHOICES,
        'all_apps': all_apps,
        'all_groups': all_groups,
        'permissions_by_app': permissions_by_app,
    }
    return render(request, 'accounts/create_user.html', context)


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
        
        # Update basic details
        user_to_edit.first_name = request.POST.get('first_name', user_to_edit.first_name)
        user_to_edit.last_name = request.POST.get('last_name', user_to_edit.last_name)
        user_to_edit.email = request.POST.get('email', user_to_edit.email)

        # Update app access
        app_ids = request.POST.getlist('apps')
        apps = App.objects.filter(id__in=app_ids, is_active=True)
        user_to_edit.assigned_apps.set(apps)
        
        # Update organization
        company_id = request.POST.get('company')
        branch_id = request.POST.get('branch')
        department_id = request.POST.get('department')
        
        user_to_edit.company_id = company_id or None
        user_to_edit.branch_id = branch_id or None
        user_to_edit.department_id = department_id or None
        
        # Update centralized approver
        user_to_edit.is_centralized_approver = request.POST.get('is_centralized_approver') == 'on'
        
        # Update active status
        user_to_edit.is_active = request.POST.get('is_active') == 'on'
        
        # Update Django permissions
        permission_ids = request.POST.getlist('permissions')
        permissions = Permission.objects.filter(id__in=permission_ids)
        user_to_edit.user_permissions.set(permissions)
        
        # Update groups
        group_ids = request.POST.getlist('groups')
        groups = Group.objects.filter(id__in=group_ids)
        user_to_edit.groups.set(groups)
        
        user_to_edit.save()
        
        messages.success(request, f'User {user_to_edit.username} updated successfully!')
        return redirect('accounts:manage_users')
    
    # GET request - show form
    all_apps = App.objects.filter(is_active=True)
    user_apps = user_to_edit.assigned_apps.all()
    companies = Company.objects.all().order_by('name')
    branches = Branch.objects.all().order_by('name')
    departments = Department.objects.all().order_by('name')
    
    # Get relevant permissions grouped by app/model
    content_types = ContentType.objects.filter(
        app_label__in=['transactions', 'workflow', 'treasury', 'reports', 'accounts', 'organization', 'settings_manager']
    ).order_by('app_label', 'model')
    
    permissions_by_app = {}
    for ct in content_types:
        app_label = ct.app_label
        if app_label not in permissions_by_app:
            permissions_by_app[app_label] = []
        
        perms = Permission.objects.filter(content_type=ct).order_by('codename')
        for perm in perms:
            permissions_by_app[app_label].append({
                'id': perm.id,
                'name': perm.name,
                'codename': perm.codename,
                'model': ct.model,
            })
    
    user_permission_ids = list(user_to_edit.user_permissions.values_list('id', flat=True))
    
    # Get all groups
    all_groups = Group.objects.all().order_by('name')
    user_group_ids = list(user_to_edit.groups.values_list('id', flat=True))
    
    context = {
        'user_to_edit': user_to_edit,
        'all_apps': all_apps,
        'user_apps': user_apps,
        'companies': companies,
        'branches': branches,
        'departments': departments,
        'roles': User.ROLE_CHOICES,
        'permissions_by_app': permissions_by_app,
        'user_permission_ids': user_permission_ids,
        'all_groups': all_groups,
        'user_group_ids': user_group_ids,
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


# ==========================================
# Permission Groups Management
# ==========================================

@login_required
@permission_required('auth.view_group', raise_exception=True)
def manage_groups(request):
    """View and manage permission groups"""
    groups = Group.objects.annotate(
        num_users=Count('user'),
        num_permissions=Count('permissions')
    ).order_by('name')
    
    context = {
        'groups': groups,
    }
    
    return render(request, 'accounts/manage_groups.html', context)


@login_required
@permission_required('auth.add_group', raise_exception=True)
def create_group(request):
    """Create a new permission group"""
    if request.method == 'POST':
        group_name = request.POST.get('name')
        permission_ids = request.POST.getlist('permissions')
        
        if group_name:
            group = Group.objects.create(name=group_name)
            
            if permission_ids:
                permissions = Permission.objects.filter(id__in=permission_ids)
                group.permissions.set(permissions)
            
            messages.success(request, f'Group "{group_name}" created successfully!')
            return redirect('accounts:manage_groups')
        else:
            messages.error(request, 'Group name is required.')
    
    # GET request - show form
    content_types = ContentType.objects.filter(
        app_label__in=['transactions', 'workflow', 'treasury', 'reports', 'accounts', 'organization', 'settings_manager']
    ).order_by('app_label', 'model')
    
    permissions_by_app = {}
    for ct in content_types:
        app_label = ct.app_label
        if app_label not in permissions_by_app:
            permissions_by_app[app_label] = []
        
        perms = Permission.objects.filter(content_type=ct).order_by('codename')
        for perm in perms:
            permissions_by_app[app_label].append({
                'id': perm.id,
                'name': perm.name,
                'codename': perm.codename,
                'model': ct.model,
            })
    
    context = {
        'permissions_by_app': permissions_by_app,
    }
    
    return render(request, 'accounts/create_group.html', context)


@login_required
@permission_required('auth.change_group', raise_exception=True)
def edit_group(request, group_id):
    """Edit an existing permission group"""
    group = get_object_or_404(Group, id=group_id)
    
    if request.method == 'POST':
        group_name = request.POST.get('name')
        permission_ids = request.POST.getlist('permissions')
        
        if group_name:
            group.name = group_name
            group.save()
            
            permissions = Permission.objects.filter(id__in=permission_ids)
            group.permissions.set(permissions)
            
            messages.success(request, f'Group "{group_name}" updated successfully!')
            return redirect('accounts:manage_groups')
        else:
            messages.error(request, 'Group name is required.')
    
    # GET request - show form
    content_types = ContentType.objects.filter(
        app_label__in=['transactions', 'workflow', 'treasury', 'reports', 'accounts', 'organization', 'settings_manager']
    ).order_by('app_label', 'model')
    
    permissions_by_app = {}
    for ct in content_types:
        app_label = ct.app_label
        if app_label not in permissions_by_app:
            permissions_by_app[app_label] = []
        
        perms = Permission.objects.filter(content_type=ct).order_by('codename')
        for perm in perms:
            permissions_by_app[app_label].append({
                'id': perm.id,
                'name': perm.name,
                'codename': perm.codename,
                'model': ct.model,
            })
    
    group_permission_ids = list(group.permissions.values_list('id', flat=True))
    
    context = {
        'group': group,
        'permissions_by_app': permissions_by_app,
        'group_permission_ids': group_permission_ids,
    }
    
    return render(request, 'accounts/edit_group.html', context)


@login_required
@permission_required('auth.delete_group', raise_exception=True)
def delete_group(request, group_id):
    """Delete a permission group"""
    group = get_object_or_404(Group, id=group_id)
    
    if request.method == 'POST':
        group_name = group.name
        group.delete()
        messages.success(request, f'Group "{group_name}" deleted successfully!')
    
    return redirect('accounts:manage_groups')

