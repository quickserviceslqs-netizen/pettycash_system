from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

# ---------------------------------------------------------------------
# Role access mapping: which apps are visible to which roles
# ---------------------------------------------------------------------
ROLE_ACCESS = {
    # Note: 'superuser' role intentionally excluded - they use Django Admin only, not user dashboard
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
    "admin",  # Admin handles escalations and overrides
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
    is_centralized = getattr(user, "is_centralized_approver", False)

    # ----------------------------
    # Apps navigation - use assigned_apps instead of ROLE_ACCESS
    # ----------------------------
    # Get apps assigned to this user
    assigned_apps = user.assigned_apps.filter(is_active=True).values_list('name', flat=True)
    
    # Fallback to role-based access if no apps assigned (backward compatibility)
    if not assigned_apps:
        assigned_apps = ROLE_ACCESS.get(user_role, [])
    
    navigation = [
        {
            "name": app.capitalize() if isinstance(app, str) else app, 
            "url": f"/{app}/"
        } 
        for app in assigned_apps
    ]
    show_no_apps_cta = not navigation

    # ----------------------------
    # Dashboard stats (personalized for each user)
    # ----------------------------
    # Show only metrics relevant to the specific user's role
    
    # My Transactions (created by me)
    my_transactions_pending = Requisition.objects.filter(
        requested_by=user,
        status__startswith="pending"
    ).count()
    
    # Pending on My Approval (assigned to me as next approver)
    pending_my_approval = Requisition.objects.filter(
        next_approver=user,
        status__startswith="pending"
    ).exclude(requested_by=user).count()
    
    # For Treasury, FP&A, CFO, CEO: Company-wide metrics (they need operational/strategic visibility)
    # Workflow overdue and reports pending are relevant to these oversight roles
    # Note: Superuser excluded - they use Django Admin, not user dashboard
    if user_role in ['treasury', 'fp&a', 'cfo', 'ceo'] or is_centralized:
        if is_centralized:
            total_transactions_pending = Requisition.objects.filter(status__startswith="pending").count()
            workflow_overdue = ApprovalTrail.objects.filter(
                requisition__status="pending",
                requisition__next_approver__isnull=False
            ).count()
            ready_for_payment_count = Requisition.objects.filter(status="reviewed").count()
        else:
            total_transactions_pending = Requisition.objects.current_company().filter(status__startswith="pending").count()
            workflow_overdue = ApprovalTrail.objects.filter(
                requisition__requested_by__company=user.company,
                requisition__status="pending",
                requisition__next_approver__isnull=False
            ).count()
            ready_for_payment_count = Requisition.objects.current_company().filter(status="reviewed").count()
    else:
        # Regular users: no need for total company metrics
        total_transactions_pending = 0
        workflow_overdue = 0
        ready_for_payment_count = 0
    
    # For centralized Treasury: breakdown by company
    company_breakdown = []
    if user_role == 'treasury' and is_centralized:
        from organization.models import Company
        companies = Company.objects.all()
        for company in companies:
            company_breakdown.append({
                'name': company.name,
                'ready_for_payment': Requisition.objects.filter(
                    requested_by__company=company,
                    status="reviewed"
                ).count()
            })

    # ----------------------------
    # Pending approvals for approvers only
    # ----------------------------
    if user_role in APPROVER_ROLES:
        # Centralized approvers see all pending requisitions across all companies
        # Regular approvers see only their company's requisitions
        if is_centralized:
            pending_for_user = Requisition.objects.filter(
                status="pending",
                next_approver=user
            ).exclude(requested_by=user)  # no-self-approval
        else:
            pending_for_user = Requisition.objects.current_company().filter(
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
        # Centralized treasury sees all companies, regular treasury sees their company only
        if is_centralized:
            ready_for_payment = Requisition.objects.filter(
                status="reviewed"
            ).select_related('requested_by', 'requested_by__company')
        else:
            ready_for_payment = Requisition.objects.current_company().filter(
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
        "is_centralized": is_centralized,
        "scope_label": "Company-Wide" if is_centralized else user.company.name if user.company else "Personal",
        "navigation": navigation,
        "show_no_apps_cta": show_no_apps_cta,
        # Personal metrics
        "my_transactions_pending": my_transactions_pending,
        "pending_my_approval": pending_my_approval,
        "ready_for_payment_count": ready_for_payment_count,
        # Company-wide metrics (for Treasury, FP&A, CEO, centralized approvers)
        "total_transactions_pending": total_transactions_pending,
        "workflow_overdue": workflow_overdue,
        "show_company_metrics": user_role in ['treasury', 'fp&a', 'cfo', 'ceo'] or is_centralized,
        "company_breakdown": company_breakdown if user_role == 'treasury' and is_centralized else [],
        "reports_pending": reports_pending,
        "pending_for_user": pending_for_user,
        "show_pending_section": show_pending_section,
        "ready_for_payment": ready_for_payment,
        "show_payment_section": show_payment_section,
        "is_approver": user_role in APPROVER_ROLES,
    }

    return render(request, "accounts/dashboard.html", context)
