from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

# ---------------------------------------------------------------------
# Role access mapping: which apps are visible to which roles
# ---------------------------------------------------------------------
ROLE_ACCESS = {
    "admin": ["transactions", "treasury", "workflow", "reports"],
    "staff": ["transactions"],  # Removed treasury for regular staff
    "treasury": ["treasury", "workflow", "transactions"],  # Phase 5: Treasury needs workflow for approval/validation
    "fp&a": ["transactions", "reports"],
    "department_head": ["workflow"],
    "branch_manager": ["workflow"],
    "regional_manager": ["workflow", "reports"],
    "group_finance_manager": ["workflow", "reports"],
    "cfo": ["reports"],
    "ceo": ["reports"],
}

# Roles that can approve requisitions
APPROVER_ROLES = {
    "admin",
    "treasury",
    "fp&a",
    "department_head",
    "branch_manager",
    "regional_manager",
    "group_finance_manager",
    "cfo",
}


# ---------------------------------------------------------------------
# Role-based redirect view
# ---------------------------------------------------------------------
@login_required
def role_based_redirect(request):
    """
    Redirect all users to the dashboard after login.
    """
    return redirect("dashboard")


# ---------------------------------------------------------------------
# Dashboard view
# ---------------------------------------------------------------------
@login_required
def dashboard(request):
    """
    Display dashboard with accessible apps and pending approvals.
    Phase 4 invariant: No-self-approval enforced.
    """
    from transactions.models import Requisition, ApprovalTrail
    try:
        from treasury.models import Payment
    except ImportError:
        Payment = None

    user = request.user
    user_role = getattr(user, "role", "").lower().strip()

    # ----------------------------
    # Apps navigation
    # ----------------------------
    apps = ROLE_ACCESS.get(user_role, [])
    navigation = [{"name": app.capitalize(), "url": f"/{app}/"} for app in apps]
    show_no_apps_cta = not apps

    # ----------------------------
    # Dashboard stats
    # ----------------------------
    total_transactions_pending = Requisition.objects.filter(
        status__startswith="pending"
    ).count()

    workflow_overdue = ApprovalTrail.objects.filter(
        requisition__status="pending",
        requisition__next_approver__isnull=False
    ).count()

    treasury_pending = 0
    if Payment:
        paid_reqs = Payment.objects.values_list('requisition_id', flat=True)
        treasury_pending = Requisition.objects.filter(
            status="pending"
        ).exclude(transaction_id__in=paid_reqs).count()

    # ----------------------------
    # Pending approvals for approvers only
    # ----------------------------
    if user_role in APPROVER_ROLES:
        pending_for_user = Requisition.objects.filter(
            status="pending",
            next_approver=user
        ).exclude(requested_by=user)  # no-self-approval
        show_pending_section = pending_for_user.exists()
    else:
        pending_for_user = Requisition.objects.none()
        show_pending_section = False

    # ----------------------------
    # Reviewed requisitions ready for payment (Treasury only)
    # ----------------------------
    if user_role == 'treasury':
        ready_for_payment = Requisition.objects.filter(
            status="reviewed"
        ).select_related('requested_by')
        show_payment_section = ready_for_payment.exists()
    else:
        ready_for_payment = Requisition.objects.none()
        show_payment_section = False

    # ----------------------------
    # Reports pending (placeholder)
    # ----------------------------
    reports_pending = 0
    # reports_pending = Report.objects.filter(status='pending').count()  # Uncomment if Report model exists

    context = {
        "user": user,
        "user_role": user_role,
        "navigation": navigation,
        "show_no_apps_cta": show_no_apps_cta,
        "total_transactions_pending": total_transactions_pending,
        "treasury_pending": treasury_pending,
        "workflow_overdue": workflow_overdue,
        "reports_pending": reports_pending,
        "pending_for_user": pending_for_user,
        "show_pending_section": show_pending_section,
        "ready_for_payment": ready_for_payment,
        "show_payment_section": show_payment_section,
        "is_approver": user_role in APPROVER_ROLES,
    }

    return render(request, "accounts/dashboard.html", context)
