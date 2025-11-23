from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from accounts.permissions import get_user_apps
from accounts.models import User
from workflow.models import ApprovalThreshold
import json


@login_required
def workflow_dashboard(request):
    """
    Workflow dashboard view - displays approval thresholds.
    Requires workflow app assignment and view_approvalthreshold permission.
    """
    # Check if user has 'workflow' app assigned
    user_apps = get_user_apps(request.user)
    if 'workflow' not in user_apps:
        messages.error(request, "You don't have access to Workflow app.")
        return redirect('dashboard')
    
    # Check if user has permission to view workflow
    if not request.user.has_perm('workflow.view_approvalthreshold'):
        messages.error(request, "You don't have permission to view approval thresholds. Required: workflow.view_approvalthreshold")
        return redirect('dashboard')
    
    # Get all thresholds
    thresholds = ApprovalThreshold.objects.all().order_by('priority', 'min_amount')
    
    # Apply filters
    origin_filter = request.GET.get('origin')
    status_filter = request.GET.get('status')
    cfo_filter = request.GET.get('cfo')
    
    if origin_filter:
        thresholds = thresholds.filter(origin_type=origin_filter)
    
    if status_filter == 'active':
        thresholds = thresholds.filter(is_active=True)
    elif status_filter == 'inactive':
        thresholds = thresholds.filter(is_active=False)
    
    if cfo_filter == 'yes':
        thresholds = thresholds.filter(requires_cfo=True)
    elif cfo_filter == 'no':
        thresholds = thresholds.filter(requires_cfo=False)
    
    # Calculate summary stats
    all_thresholds = ApprovalThreshold.objects.all()
    active_count = all_thresholds.filter(is_active=True).count()
    origin_types = all_thresholds.values_list('origin_type', flat=True).distinct()
    fasttrack_count = all_thresholds.filter(allow_urgent_fasttrack=True, is_active=True).count()
    cfo_count = all_thresholds.filter(requires_cfo=True, is_active=True).count()
    
    context = {
        'thresholds': thresholds,
        'active_count': active_count,
        'origin_types': origin_types,
        'fasttrack_count': fasttrack_count,
        'cfo_count': cfo_count,
    }
    
    return render(request, 'workflow/dashboard.html', context)


@login_required
def threshold_edit(request, threshold_id):
    """
    Edit approval threshold with drag-and-drop interface.
    Requires workflow app assignment and change_approvalthreshold permission.
    """
    # Check if user has 'workflow' app assigned
    user_apps = get_user_apps(request.user)
    if 'workflow' not in user_apps:
        messages.error(request, "You don't have access to Workflow app.")
        return redirect('dashboard')
    
    # Check if user has permission to change workflow thresholds
    if not request.user.has_perm('workflow.change_approvalthreshold'):
        messages.error(request, "You don't have permission to edit approval thresholds. Required: workflow.change_approvalthreshold")
        return redirect('workflow:dashboard')
    
    threshold = get_object_or_404(ApprovalThreshold, id=threshold_id)
    
    # Get available approver roles (excluding staff and admin which aren't approvers)
    approver_roles = [
        ('branch_manager', 'Branch Manager'),
        ('department_head', 'Department Head'),
        ('regional_manager', 'Regional Manager'),
        ('group_finance_manager', 'Group Finance Manager'),
        ('cfo', 'CFO'),
        ('ceo', 'CEO'),
    ]
    
    if request.method == 'POST':
        try:
            # Get form data
            threshold.name = request.POST.get('name')
            threshold.origin_type = request.POST.get('origin_type')
            threshold.min_amount = request.POST.get('min_amount')
            threshold.max_amount = request.POST.get('max_amount')
            threshold.priority = request.POST.get('priority')
            threshold.allow_urgent_fasttrack = request.POST.get('allow_urgent_fasttrack') == 'on'
            threshold.requires_cfo = request.POST.get('requires_cfo') == 'on'
            threshold.requires_ceo = request.POST.get('requires_ceo') == 'on'
            threshold.is_active = request.POST.get('is_active') == 'on'
            
            # Get roles sequence from JSON
            roles_sequence_json = request.POST.get('roles_sequence')
            if roles_sequence_json:
                threshold.roles_sequence = json.loads(roles_sequence_json)
            else:
                threshold.roles_sequence = []
            
            # Validate at least one approver
            if not threshold.roles_sequence:
                messages.error(request, "Please add at least one approver to the sequence.")
                context = {
                    'threshold': threshold,
                    'available_roles': approver_roles,
                }
                return render(request, 'workflow/threshold_edit.html', context)
            
            threshold.save()
            messages.success(request, f"Approval threshold '{threshold.name}' updated successfully!")
            return redirect('workflow:dashboard')
            
        except Exception as e:
            messages.error(request, f"Error updating threshold: {str(e)}")
    
    context = {
        'threshold': threshold,
        'available_roles': approver_roles,
    }
    
    return render(request, 'workflow/threshold_edit.html', context)
