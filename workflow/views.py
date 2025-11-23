from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.permissions import get_user_apps
from workflow.models import ApprovalThreshold


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
