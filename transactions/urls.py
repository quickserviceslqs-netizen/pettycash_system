from django.contrib.auth.decorators import login_required
from django.urls import path

from accounts.permissions import require_app_access
from transactions.views import admin_override_approval  # Phase 4: Admin override
from transactions.views import confirm_urgency  # Phase 3: Urgency confirmation
from transactions.views import (
    my_requisitions,  # Separate view for user's own requisitions
)
from transactions.views import (
    pending_approvals,  # Separate view for requisitions awaiting approval
)
from transactions.views import (
    request_changes,  # Approver requests changes from requester
)
from transactions.views import (
    revert_fast_track,  # Revert fast-tracked requisition to normal flow
)
from transactions.views import submit_changes  # Requester submits requested changes
from transactions.views import (
    approve_requisition,
    create_requisition,
    reject_requisition,
    requisition_detail,
    transactions_home,
)
from transactions.views_admin import approve_requisition as approve_req_admin
from transactions.views_admin import create_requisition as create_req_admin
from transactions.views_admin import manage_requisitions
from transactions.views_admin import reject_requisition as reject_req_admin
from transactions.views_admin import view_requisition

app_name = "transactions"

# ---------------------------------------------------------------------
# URL patterns - using app assignment + Django permissions
# ---------------------------------------------------------------------
urlpatterns = [
    # Admin requisition management
    path("admin/requisitions/", manage_requisitions, name="manage_requisitions"),
    path("admin/requisitions/create/", create_req_admin, name="create_requisition"),
    path(
        "admin/requisitions/<str:transaction_id>/",
        view_requisition,
        name="view_requisition",
    ),
    path(
        "admin/requisitions/<str:transaction_id>/approve/",
        approve_req_admin,
        name="approve_requisition",
    ),
    path(
        "admin/requisitions/<str:transaction_id>/reject/",
        reject_req_admin,
        name="reject_requisition",
    ),
    # Main transactions page - requires transactions app + view permission
    path("", transactions_home, name="transactions-home"),
    # Separate views for approvers (avoid confusion between own vs. approval queue)
    path("my-requisitions/", login_required(my_requisitions), name="my-requisitions"),
    path(
        "pending-approvals/",
        login_required(pending_approvals),
        name="pending-approvals",
    ),
    # Create requisition - requires transactions app + add permission
    path("create/", login_required(create_requisition), name="create-requisition"),
    # Approve/reject - handled by view permission checks
    path(
        "approve/<str:requisition_id>/",
        login_required(approve_requisition),
        name="approve-requisition",
    ),
    path(
        "reject/<str:requisition_id>/",
        login_required(reject_requisition),
        name="reject-requisition",
    ),
    # Phase 3: Urgency confirmation by first approver
    path(
        "confirm-urgency/<str:requisition_id>/",
        login_required(confirm_urgency),
        name="confirm-urgency",
    ),
    # Revert fast-tracked requisition to normal approval flow
    path(
        "revert-fast-track/<str:requisition_id>/",
        login_required(revert_fast_track),
        name="revert-fast-track",
    ),
    # Request changes from requester instead of rejecting
    path(
        "request-changes/<str:requisition_id>/",
        login_required(request_changes),
        name="request-changes",
    ),
    # Requester submits requested changes
    path(
        "submit-changes/<str:requisition_id>/",
        login_required(submit_changes),
        name="submit-changes",
    ),
    # Phase 4: Admin override (emergency approval) - requires change permission
    path(
        "admin-override/<str:requisition_id>/",
        login_required(admin_override_approval),
        name="admin-override",
    ),
    # Requisition detail page
    path(
        "detail/<str:requisition_id>/",
        login_required(requisition_detail),
        name="requisition-detail",
    ),
]
