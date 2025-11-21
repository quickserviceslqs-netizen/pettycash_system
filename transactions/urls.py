from django.urls import path
from django.contrib.auth.decorators import login_required, user_passes_test
from transactions.views import (
    transactions_home,
    create_requisition,
    approve_requisition,
    reject_requisition,
    requisition_detail,
    confirm_urgency,  # Phase 3: Urgency confirmation
)

# ---------------------------------------------------------------------
# Role-based access decorator
# ---------------------------------------------------------------------
def role_required(allowed_roles):
    """
    Decorator for views to check if the logged-in user's role
    is in the allowed_roles list.
    """
    def check_role(user):
        return user.is_authenticated and getattr(user, "role", "").lower() in allowed_roles
    return user_passes_test(check_role)

# Common roles allowed to access transactions
TRANSACTION_ROLES = [
    'admin', 'staff', 'fp&a', 'department_head',
    'branch_manager', 'regional_manager', 'group_finance_manager'
]

# Wrapper to apply login + role_required (used for approver-only views)
def protected(view):
    return login_required(role_required(TRANSACTION_ROLES)(view))

# ---------------------------------------------------------------------
# URL patterns
# ---------------------------------------------------------------------
urlpatterns = [
    path('', protected(transactions_home), name='transactions-home'),
    # Allow any authenticated user to create a requisition (no role restriction)
    path('create/', login_required(create_requisition), name='create-requisition'),
    path('approve/<uuid:requisition_id>/', protected(approve_requisition), name='approve-requisition'),
    path('reject/<uuid:requisition_id>/', protected(reject_requisition), name='reject-requisition'),
    
    # Phase 3: Urgency confirmation by first approver
    path('confirm-urgency/<uuid:requisition_id>/', protected(confirm_urgency), name='confirm-urgency'),

    # Requisition detail page
    path('detail/<uuid:requisition_id>/', protected(requisition_detail), name='requisition-detail'),
]
