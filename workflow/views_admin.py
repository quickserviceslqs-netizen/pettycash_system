"""
Workflow Admin Views
User-friendly interface for managing approval thresholds
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Q, Count
from workflow.models import ApprovalThreshold
from accounts.models import User
import json


@login_required
@permission_required('workflow.view_approvalthreshold', raise_exception=True)
def manage_thresholds(request):
    """View all approval thresholds"""
    
    # Filters
    origin_filter = request.GET.get('origin', '')
    status_filter = request.GET.get('status', '')
    
    thresholds = ApprovalThreshold.objects.all()
    
    if origin_filter:
        thresholds = thresholds.filter(origin_type=origin_filter)
    
    if status_filter == 'active':
        thresholds = thresholds.filter(is_active=True)
    elif status_filter == 'inactive':
        thresholds = thresholds.filter(is_active=False)
    
    thresholds = thresholds.order_by('priority', 'min_amount')
    
    context = {
        'thresholds': thresholds,
        'origin_filter': origin_filter,
        'status_filter': status_filter,
        'origin_choices': ApprovalThreshold.ORIGIN_CHOICES,
    }
    
    return render(request, 'workflow/manage_thresholds.html', context)


@login_required
@permission_required('workflow.add_approvalthreshold', raise_exception=True)
def create_threshold(request):
    """Create a new approval threshold"""
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.POST.get('name')
            origin_type = request.POST.get('origin_type')
            min_amount = request.POST.get('min_amount')
            max_amount = request.POST.get('max_amount')
            priority = request.POST.get('priority', 0)
            allow_urgent_fasttrack = request.POST.get('allow_urgent_fasttrack') == 'on'
            requires_cfo = request.POST.get('requires_cfo') == 'on'
            requires_ceo = request.POST.get('requires_ceo') == 'on'
            is_active = request.POST.get('is_active') == 'on'
            
            # Get roles sequence (as JSON array)
            roles_sequence = request.POST.getlist('roles')
            
            # Validate
            if not name or not origin_type or not roles_sequence:
                messages.error(request, 'Name, origin type, and at least one role are required.')
                return redirect('workflow:create_threshold')
            
            # Create threshold
            threshold = ApprovalThreshold.objects.create(
                name=name,
                origin_type=origin_type,
                min_amount=min_amount or 0,
                max_amount=max_amount or 999999999,
                roles_sequence=roles_sequence,
                priority=priority or 0,
                allow_urgent_fasttrack=allow_urgent_fasttrack,
                requires_cfo=requires_cfo,
                requires_ceo=requires_ceo,
                is_active=is_active,
            )
            
            messages.success(request, f'Approval threshold "{name}" created successfully!')
            return redirect('workflow:manage_thresholds')
            
        except Exception as e:
            messages.error(request, f'Error creating threshold: {str(e)}')
    
    # GET request - show form
    # Get available roles from User model
    available_roles = User.ROLE_CHOICES
    
    context = {
        'origin_choices': ApprovalThreshold.ORIGIN_CHOICES,
        'available_roles': available_roles,
    }
    
    return render(request, 'workflow/create_threshold.html', context)


@login_required
@permission_required('workflow.change_approvalthreshold', raise_exception=True)
def edit_threshold(request, threshold_id):
    """Edit an existing approval threshold"""
    
    threshold = get_object_or_404(ApprovalThreshold, id=threshold_id)
    
    if request.method == 'POST':
        try:
            # Update data
            threshold.name = request.POST.get('name')
            threshold.origin_type = request.POST.get('origin_type')
            threshold.min_amount = request.POST.get('min_amount') or 0
            threshold.max_amount = request.POST.get('max_amount') or 999999999
            threshold.priority = request.POST.get('priority', 0) or 0
            threshold.allow_urgent_fasttrack = request.POST.get('allow_urgent_fasttrack') == 'on'
            threshold.requires_cfo = request.POST.get('requires_cfo') == 'on'
            threshold.requires_ceo = request.POST.get('requires_ceo') == 'on'
            threshold.is_active = request.POST.get('is_active') == 'on'
            
            # Update roles sequence
            roles_sequence = request.POST.getlist('roles')
            if roles_sequence:
                threshold.roles_sequence = roles_sequence
            
            threshold.save()
            
            messages.success(request, f'Threshold "{threshold.name}" updated successfully!')
            return redirect('workflow:manage_thresholds')
            
        except Exception as e:
            messages.error(request, f'Error updating threshold: {str(e)}')
    
    # GET request - show form
    available_roles = User.ROLE_CHOICES
    
    context = {
        'threshold': threshold,
        'origin_choices': ApprovalThreshold.ORIGIN_CHOICES,
        'available_roles': available_roles,
        'roles_json': json.dumps(threshold.roles_sequence),
    }
    
    return render(request, 'workflow/edit_threshold.html', context)


@login_required
@permission_required('workflow.delete_approvalthreshold', raise_exception=True)
def delete_threshold(request, threshold_id):
    """Delete an approval threshold"""
    
    threshold = get_object_or_404(ApprovalThreshold, id=threshold_id)
    
    if request.method == 'POST':
        threshold_name = threshold.name
        threshold.delete()
        messages.success(request, f'Threshold "{threshold_name}" deleted successfully!')
    
    return redirect('workflow:manage_thresholds')


@login_required
@permission_required('workflow.change_approvalthreshold', raise_exception=True)
def toggle_threshold_status(request, threshold_id):
    """Toggle threshold active status"""
    
    threshold = get_object_or_404(ApprovalThreshold, id=threshold_id)
    
    if request.method == 'POST':
        threshold.is_active = not threshold.is_active
        threshold.save()
        
        status = "activated" if threshold.is_active else "deactivated"
        messages.success(request, f'Threshold "{threshold.name}" {status}!')
    
    return redirect('workflow:manage_thresholds')
