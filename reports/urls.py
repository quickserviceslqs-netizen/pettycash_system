from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import redirect
from django.contrib import messages
from django.views import View
from accounts.permissions import get_user_apps

# ---------------------------------------------------------------------
# Custom view with permission checks
# ---------------------------------------------------------------------
class ReportsDashboardView(View):
    """Reports dashboard - requires reports app access and view permission."""
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        # Check if user has 'reports' app assigned
        user_apps = get_user_apps(request.user)
        if 'reports' not in user_apps:
            messages.error(request, "You don't have access to Reports app.")
            return redirect('dashboard')
        
        # Check if user has permission to view reports
        if not request.user.has_perm('reports.view_report'):
            messages.error(request, "You don't have permission to view reports.")
            return redirect('dashboard')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        from django.shortcuts import render
        return render(request, 'reports/dashboard.html')

# ---------------------------------------------------------------------
# URL patterns
# ---------------------------------------------------------------------
urlpatterns = [
    path('', ReportsDashboardView.as_view(), name='reports-home'),
    path('dashboard/', ReportsDashboardView.as_view(), name='reports-dashboard'),
]
