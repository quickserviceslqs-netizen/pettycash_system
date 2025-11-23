from django.urls import path
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from accounts.permissions import get_user_apps

# ---------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------
@login_required
def workflow_home(request):
    """Workflow home page - requires workflow app access."""
    # Check if user has 'workflow' app assigned
    user_apps = get_user_apps(request.user)
    if 'workflow' not in user_apps:
        messages.error(request, "You don't have access to Workflow app.")
        return redirect('dashboard')
    
    # Check if user has permission to view workflow
    if not request.user.has_perm('workflow.view_approvalthreshold'):
        messages.error(request, "You don't have permission to view workflow.")
        return redirect('dashboard')
    
    return HttpResponse("Workflow Home - Approval Thresholds Management")

# ---------------------------------------------------------------------
# URL patterns
# ---------------------------------------------------------------------
urlpatterns = [
    path('', workflow_home, name='workflow-home'),
]
