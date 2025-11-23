"""
Organization Admin Views
Provides UI for managing Cost Centers and Positions.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Count

from organization.models import CostCenter, Position, Department, Branch, Region, Company
from accounts.models import User


def is_admin_user(user):
    """Check if user is superuser or has admin role"""
    return user.is_superuser or user.role == 'admin'


# ===========================
# Cost Center Management
# ===========================

@login_required
@user_passes_test(is_admin_user)
def manage_cost_centers(request):
    """
    Dashboard for managing cost centers.
    Shows all cost centers with filtering by department/branch.
    """
    cost_centers = CostCenter.objects.select_related(
        'department', 'department__branch', 'department__branch__region'
    ).annotate(
        user_count=Count('user')
    ).order_by('department__branch__name', 'department__name', 'name')
    
    # Filters
    department_filter = request.GET.get('department', '')
    branch_filter = request.GET.get('branch', '')
    search_query = request.GET.get('search', '').strip()
    
    if department_filter:
        cost_centers = cost_centers.filter(department_id=department_filter)
    
    if branch_filter:
        cost_centers = cost_centers.filter(department__branch_id=branch_filter)
    
    if search_query:
        cost_centers = cost_centers.filter(
            Q(name__icontains=search_query) |
            Q(department__name__icontains=search_query)
        )
    
    # Statistics
    stats = {
        'total': CostCenter.objects.count(),
        'total_assignments': User.objects.filter(cost_center__isnull=False).count(),
    }
    
    # Get all departments and branches for filters
    departments = Department.objects.select_related('branch').order_by('branch__name', 'name')
    branches = Branch.objects.select_related('region').order_by('region__name', 'name')
    
    context = {
        'cost_centers': cost_centers,
        'stats': stats,
        'departments': departments,
        'branches': branches,
        'filters': {
            'department': department_filter,
            'branch': branch_filter,
            'search': search_query,
        }
    }
    
    return render(request, 'organization/manage_cost_centers.html', context)


@login_required
@user_passes_test(is_admin_user)
def create_cost_center(request):
    """Create a new cost center."""
    if request.method == 'POST':
        name = request.POST.get('name')
        department_id = request.POST.get('department')
        
        if not name or not department_id:
            messages.error(request, "Name and department are required.")
            return redirect('organization:create_cost_center')
        
        department = get_object_or_404(Department, id=department_id)
        
        # Check for duplicates
        if CostCenter.objects.filter(name=name, department=department).exists():
            messages.error(request, f"Cost center '{name}' already exists in {department.name}.")
            return redirect('organization:create_cost_center')
        
        cost_center = CostCenter.objects.create(
            name=name,
            department=department
        )
        
        messages.success(request, f"Cost center '{cost_center.name}' created successfully.")
        return redirect('organization:manage_cost_centers')
    
    # Get all departments grouped by branch
    departments = Department.objects.select_related('branch', 'branch__region').order_by(
        'branch__region__name', 'branch__name', 'name'
    )
    
    context = {
        'departments': departments,
    }
    return render(request, 'organization/create_cost_center.html', context)


@login_required
@user_passes_test(is_admin_user)
def edit_cost_center(request, cost_center_id):
    """Edit an existing cost center."""
    cost_center = get_object_or_404(
        CostCenter.objects.select_related('department', 'department__branch'),
        id=cost_center_id
    )
    
    if request.method == 'POST':
        name = request.POST.get('name')
        department_id = request.POST.get('department')
        
        if not name or not department_id:
            messages.error(request, "Name and department are required.")
            return redirect('organization:edit_cost_center', cost_center_id=cost_center_id)
        
        department = get_object_or_404(Department, id=department_id)
        
        # Check for duplicates (excluding current)
        if CostCenter.objects.filter(name=name, department=department).exclude(id=cost_center.id).exists():
            messages.error(request, f"Cost center '{name}' already exists in {department.name}.")
            return redirect('organization:edit_cost_center', cost_center_id=cost_center_id)
        
        cost_center.name = name
        cost_center.department = department
        cost_center.save()
        
        messages.success(request, f"Cost center '{cost_center.name}' updated successfully.")
        return redirect('organization:manage_cost_centers')
    
    # Get assigned users
    assigned_users = User.objects.filter(cost_center=cost_center).select_related(
        'department', 'branch', 'company'
    ).order_by('first_name', 'last_name')
    
    # Get all departments
    departments = Department.objects.select_related('branch', 'branch__region').order_by(
        'branch__region__name', 'branch__name', 'name'
    )
    
    context = {
        'cost_center': cost_center,
        'assigned_users': assigned_users,
        'departments': departments,
    }
    return render(request, 'organization/edit_cost_center.html', context)


@login_required
@user_passes_test(is_admin_user)
def delete_cost_center(request, cost_center_id):
    """Delete a cost center (only if no users assigned)."""
    if request.method == 'POST':
        cost_center = get_object_or_404(CostCenter, id=cost_center_id)
        
        # Check if any users assigned
        user_count = User.objects.filter(cost_center=cost_center).count()
        if user_count > 0:
            messages.error(
                request,
                f"Cannot delete cost center '{cost_center.name}' - {user_count} users are assigned to it."
            )
            return redirect('organization:manage_cost_centers')
        
        name = cost_center.name
        cost_center.delete()
        
        messages.success(request, f"Cost center '{name}' deleted successfully.")
        return redirect('organization:manage_cost_centers')
    
    return redirect('organization:manage_cost_centers')


# ===========================
# Position Management
# ===========================

@login_required
@user_passes_test(is_admin_user)
def manage_positions(request):
    """
    Dashboard for managing positions/job titles.
    Shows all positions with filtering by department/branch.
    """
    positions = Position.objects.select_related(
        'department', 'department__branch', 'department__branch__region'
    ).annotate(
        user_count=Count('user')
    ).order_by('department__branch__name', 'department__name', 'title')
    
    # Filters
    department_filter = request.GET.get('department', '')
    branch_filter = request.GET.get('branch', '')
    search_query = request.GET.get('search', '').strip()
    
    if department_filter:
        positions = positions.filter(department_id=department_filter)
    
    if branch_filter:
        positions = positions.filter(department__branch_id=branch_filter)
    
    if search_query:
        positions = positions.filter(
            Q(title__icontains=search_query) |
            Q(department__name__icontains=search_query)
        )
    
    # Statistics
    stats = {
        'total': Position.objects.count(),
        'total_assignments': User.objects.filter(position_title__isnull=False).count(),
    }
    
    # Get all departments and branches for filters
    departments = Department.objects.select_related('branch').order_by('branch__name', 'name')
    branches = Branch.objects.select_related('region').order_by('region__name', 'name')
    
    context = {
        'positions': positions,
        'stats': stats,
        'departments': departments,
        'branches': branches,
        'filters': {
            'department': department_filter,
            'branch': branch_filter,
            'search': search_query,
        }
    }
    
    return render(request, 'organization/manage_positions.html', context)


@login_required
@user_passes_test(is_admin_user)
def create_position(request):
    """Create a new position/job title."""
    if request.method == 'POST':
        title = request.POST.get('title')
        department_id = request.POST.get('department')
        
        if not title or not department_id:
            messages.error(request, "Title and department are required.")
            return redirect('organization:create_position')
        
        department = get_object_or_404(Department, id=department_id)
        
        # Check for duplicates
        if Position.objects.filter(title=title, department=department).exists():
            messages.error(request, f"Position '{title}' already exists in {department.name}.")
            return redirect('organization:create_position')
        
        position = Position.objects.create(
            title=title,
            department=department
        )
        
        messages.success(request, f"Position '{position.title}' created successfully.")
        return redirect('organization:manage_positions')
    
    # Get all departments grouped by branch
    departments = Department.objects.select_related('branch', 'branch__region').order_by(
        'branch__region__name', 'branch__name', 'name'
    )
    
    context = {
        'departments': departments,
    }
    return render(request, 'organization/create_position.html', context)


@login_required
@user_passes_test(is_admin_user)
def edit_position(request, position_id):
    """Edit an existing position/job title."""
    position = get_object_or_404(
        Position.objects.select_related('department', 'department__branch'),
        id=position_id
    )
    
    if request.method == 'POST':
        title = request.POST.get('title')
        department_id = request.POST.get('department')
        
        if not title or not department_id:
            messages.error(request, "Title and department are required.")
            return redirect('organization:edit_position', position_id=position_id)
        
        department = get_object_or_404(Department, id=department_id)
        
        # Check for duplicates (excluding current)
        if Position.objects.filter(title=title, department=department).exclude(id=position.id).exists():
            messages.error(request, f"Position '{title}' already exists in {department.name}.")
            return redirect('organization:edit_position', position_id=position_id)
        
        position.title = title
        position.department = department
        position.save()
        
        messages.success(request, f"Position '{position.title}' updated successfully.")
        return redirect('organization:manage_positions')
    
    # Get assigned users
    assigned_users = User.objects.filter(position_title=position).select_related(
        'department', 'branch', 'company'
    ).order_by('first_name', 'last_name')
    
    # Get all departments
    departments = Department.objects.select_related('branch', 'branch__region').order_by(
        'branch__region__name', 'branch__name', 'name'
    )
    
    context = {
        'position': position,
        'assigned_users': assigned_users,
        'departments': departments,
    }
    return render(request, 'organization/edit_position.html', context)


@login_required
@user_passes_test(is_admin_user)
def delete_position(request, position_id):
    """Delete a position (only if no users assigned)."""
    if request.method == 'POST':
        position = get_object_or_404(Position, id=position_id)
        
        # Check if any users assigned
        user_count = User.objects.filter(position_title=position).count()
        if user_count > 0:
            messages.error(
                request,
                f"Cannot delete position '{position.title}' - {user_count} users are assigned to it."
            )
            return redirect('organization:manage_positions')
        
        title = position.title
        position.delete()
        
        messages.success(request, f"Position '{title}' deleted successfully.")
        return redirect('organization:manage_positions')
    
    return redirect('organization:manage_positions')
