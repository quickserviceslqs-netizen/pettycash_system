from django.urls import path
from django.http import HttpResponse
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

# ---------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------
@login_required
@role_required(['admin', 'fp&a', 'regional_manager', 'group_finance_manager', 'cfo', 'ceo'])
def reports_home(request):
    return HttpResponse("Reports Home")

# ---------------------------------------------------------------------
# URL patterns
# ---------------------------------------------------------------------
urlpatterns = [
    path('', reports_home, name='reports-home'),
]
