from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required, user_passes_test

# ---------------------------------------------------------------------
# Role-based access decorator
# ---------------------------------------------------------------------
def role_required(allowed_roles):
    """
    Decorator to restrict access based on user's role.
    """
    def check_role(user):
        return user.is_authenticated and user.role_key in allowed_roles
    return user_passes_test(check_role)

# Create dashboard view with role requirement
dashboard_view = login_required(
    role_required(['admin', 'fp&a', 'regional_manager', 'group_finance_manager', 'cfo', 'ceo'])(
        TemplateView.as_view(template_name='reports/dashboard.html')
    )
)

# ---------------------------------------------------------------------
# URL patterns
# ---------------------------------------------------------------------
urlpatterns = [
    path('', dashboard_view, name='reports-home'),
    path('dashboard/', dashboard_view, name='reports-dashboard'),
]
