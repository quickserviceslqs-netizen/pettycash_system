from django.urls import path
from django.contrib.auth.decorators import login_required
from transactions.views import (
    transactions_home,
    create_requisition,
    approve_requisition,
    reject_requisition,
    requisition_detail,
    confirm_urgency,  # Phase 3: Urgency confirmation
    admin_override_approval,  # Phase 4: Admin override
    revert_fast_track,  # Revert fast-tracked requisition to normal flow
    request_changes,  # Approver requests changes from requester
    submit_changes,  # Requester submits requested changes
    my_requisitions,  # Separate view for user's own requisitions
    pending_approvals,  # Separate view for requisitions awaiting approval
)
from transactions.views_admin import (
    manage_requisitions,
    create_requisition as create_req_admin,
    view_requisition,
    approve_requisition as approve_req_admin,
    reject_requisition as reject_req_admin,
)
from accounts.permissions import require_app_access

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
