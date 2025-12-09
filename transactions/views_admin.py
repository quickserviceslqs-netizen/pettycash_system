"""
Transactions Admin Views
User-friendly interface for managing requisitions and approval workflow
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from decimal import Decimal
from transactions.models import Requisition, ApprovalTrail
from workflow.models import ApprovalThreshold
from workflow.services.resolver import find_approval_threshold, resolve_workflow
from organization.models import Company, Region, Branch, Department
from accounts.models import User


@login_required
def manage_requisitions(request):
    """View and filter all requisitions"""

    # Filters
    status_filter = request.GET.get("status", "")
    user_filter = request.GET.get("user", "")
    department_filter = request.GET.get("department", "")
    search_query = request.GET.get("search", "")
    my_requisitions = request.GET.get("my_requisitions", "") == "on"
    my_approvals = request.GET.get("my_approvals", "") == "on"

    requisitions = (
        Requisition.objects.all()
        .select_related(
            "requested_by",
            "company",
            "region",
            "branch",
            "department",
            "applied_threshold",
            "next_approver",
        )
        .prefetch_related("approvaltrail_set")
    )

    # Filter by user context
    if my_requisitions:
        requisitions = requisitions.filter(requested_by=request.user)
    elif my_approvals:
        requisitions = requisitions.filter(
            next_approver=request.user,
            status__in=["pending", "pending_urgency_confirmation"],
        )

    # Additional filters
    if status_filter:
        requisitions = requisitions.filter(status=status_filter)

    if user_filter:
        requisitions = requisitions.filter(requested_by_id=user_filter)

    if department_filter:
        requisitions = requisitions.filter(department_id=department_filter)

    if search_query:
        requisitions = requisitions.filter(
            Q(transaction_id__icontains=search_query)
            | Q(purpose__icontains=search_query)
        )

    requisitions = requisitions.order_by("-created_at")[:200]  # Limit to 200 recent

    # Stats
    stats = {
        "total": Requisition.objects.count(),
        "pending": Requisition.objects.filter(
            status__in=["pending", "pending_urgency_confirmation"]
        ).count(),
        "paid": Requisition.objects.filter(status="paid").count(),
        "rejected": Requisition.objects.filter(status="rejected").count(),
        "my_pending_approvals": Requisition.objects.filter(
            next_approver=request.user,
            status__in=["pending", "pending_urgency_confirmation"],
        ).count(),
    }

    users = User.objects.filter(is_active=True).order_by("first_name", "last_name")
    departments = Department.objects.all()

    context = {
        "requisitions": requisitions,
        "stats": stats,
        "status_filter": status_filter,
        "user_filter": user_filter,
        "department_filter": department_filter,
        "search_query": search_query,
        "my_requisitions": my_requisitions,
        "my_approvals": my_approvals,
        "users": users,
        "departments": departments,
        "status_choices": Requisition.STATUS_CHOICES,
    }

    return render(request, "transactions/manage_requisitions.html", context)


@login_required
@permission_required("transactions.add_requisition", raise_exception=True)
def create_requisition(request):
    """Create a new requisition"""

    if request.method == "POST":
        try:
            # Get form data
            origin_type = request.POST.get("origin_type")
            amount = Decimal(request.POST.get("amount"))
            purpose = request.POST.get("purpose")
            is_urgent = request.POST.get("is_urgent") == "on"
            urgency_reason = request.POST.get("urgency_reason", "")

            company_id = request.POST.get("company") or None
            region_id = request.POST.get("region") or None
            branch_id = request.POST.get("branch") or None
            department_id = request.POST.get("department") or None

            # Validate required fields
            if not all([origin_type, purpose]) or amount <= 0:
                messages.error(request, "All required fields must be filled correctly.")
                return redirect("transactions:create_requisition")

            # Create requisition
            requisition = Requisition.objects.create(
                requested_by=request.user,
                origin_type=origin_type,
                company_id=company_id,
                region_id=region_id,
                branch_id=branch_id,
                department_id=department_id,
                amount=amount,
                purpose=purpose,
                is_urgent=is_urgent,
                urgency_reason=urgency_reason if is_urgent else None,
                status="draft",
            )

            # Apply approval threshold
            try:
                threshold = find_approval_threshold(amount, origin_type)
                if threshold:
                    requisition.applied_threshold = threshold
                    requisition.tier = threshold.name
                    requisition.save()

                    # Resolve workflow
                    workflow = resolve_workflow(requisition)
                    requisition.workflow_sequence = workflow
                    requisition.status = "pending"
                    requisition.save()

                    messages.success(
                        request,
                        f"Requisition {requisition.transaction_id} created successfully! Applied threshold: {threshold.name}",
                    )
                else:
                    messages.warning(
                        request,
                        f"Requisition {requisition.transaction_id} created but no matching approval threshold found. Please contact admin.",
                    )
            except Exception as e:
                messages.warning(
                    request, f"Requisition created but workflow setup failed: {str(e)}"
                )

            return redirect(
                "transactions:view_requisition",
                transaction_id=requisition.transaction_id,
            )

        except Exception as e:
            messages.error(request, f"Error creating requisition: {str(e)}")

    companies = Company.objects.all()
    regions = Region.objects.all()
    branches = Branch.objects.all()
    departments = Department.objects.all()
    thresholds = ApprovalThreshold.objects.filter(is_active=True).order_by("min_amount")

    context = {
        "companies": companies,
        "regions": regions,
        "branches": branches,
        "departments": departments,
        "thresholds": thresholds,
        "origin_choices": Requisition.ORIGIN_CHOICES,
    }

    return render(request, "transactions/create_requisition.html", context)


@login_required
def view_requisition(request, transaction_id):
    """View detailed requisition with approval trail"""

    requisition = get_object_or_404(
        Requisition.objects.select_related(
            "requested_by",
            "company",
            "region",
            "branch",
            "department",
            "applied_threshold",
            "next_approver",
        ),
        transaction_id=transaction_id,
    )

    # Check permission - must be requester, approver, or have view permission
    can_view = (
        requisition.requested_by == request.user
        or requisition.next_approver == request.user
        or request.user.has_perm("transactions.view_requisition")
    )

    if not can_view:
        messages.error(request, "You do not have permission to view this requisition.")
        return redirect("transactions:manage_requisitions")

    # Get approval trail
    approval_trail = (
        ApprovalTrail.objects.filter(requisition=requisition)
        .select_related("user")
        .order_by("timestamp")
    )

    # Check if user can approve
    can_approve = requisition.can_approve(request.user)

    # Get related payments
    payments = requisition.payments.all().select_related("executor")

    context = {
        "requisition": requisition,
        "approval_trail": approval_trail,
        "can_approve": can_approve,
        "payments": payments,
    }

    return render(request, "transactions/view_requisition.html", context)


@login_required
@permission_required("transactions.change_requisition", raise_exception=True)
def approve_requisition(request, transaction_id):
    """Approve a pending requisition"""

    requisition = get_object_or_404(Requisition, transaction_id=transaction_id)

    # Verify user can approve
    if not requisition.can_approve(request.user):
        messages.error(request, "You cannot approve this requisition.")
        return redirect("transactions:view_requisition", transaction_id=transaction_id)

    if request.method == "POST":
        try:
            comment = request.POST.get("comment", "")

            # Create approval trail entry
            ApprovalTrail.objects.create(
                requisition=requisition,
                user=request.user,
                role=request.user.role,
                action="approved",
                comment=comment,
                ip_address=request.META.get("REMOTE_ADDR"),
            )

            # Move workflow forward
            workflow = requisition.workflow_sequence or []
            if workflow:
                # Remove current approver from workflow
                workflow = workflow[1:] if len(workflow) > 1 else []
                requisition.workflow_sequence = workflow

                if workflow:
                    # Set next approver
                    next_role = workflow[0]
                    # Find user with this role in same company
                    next_approver = User.objects.filter(
                        role=next_role, company=requisition.company, is_active=True
                    ).first()
                    requisition.next_approver = next_approver
                    requisition.status = "pending"
                else:
                    # Workflow complete - mark as paid (ready for payment)
                    requisition.next_approver = None
                    requisition.status = "paid"

            requisition.save()

            messages.success(
                request, f"Requisition {transaction_id} approved successfully!"
            )
            return redirect(
                "transactions:view_requisition", transaction_id=transaction_id
            )

        except Exception as e:
            messages.error(request, f"Error approving requisition: {str(e)}")

    context = {
        "requisition": requisition,
    }

    return render(request, "transactions/approve_requisition.html", context)


@login_required
@permission_required("transactions.change_requisition", raise_exception=True)
def reject_requisition(request, transaction_id):
    """Reject a pending requisition"""

    requisition = get_object_or_404(Requisition, transaction_id=transaction_id)

    # Verify user can reject (must be next approver or have permission)
    can_reject = requisition.next_approver == request.user or request.user.has_perm(
        "transactions.delete_requisition"
    )

    if not can_reject:
        messages.error(request, "You cannot reject this requisition.")
        return redirect("transactions:view_requisition", transaction_id=transaction_id)

    if request.method == "POST":
        try:
            reason = request.POST.get("reason", "")

            if not reason:
                messages.error(request, "Rejection reason is required.")
                return redirect(
                    "transactions:reject_requisition", transaction_id=transaction_id
                )

            # Create approval trail entry
            ApprovalTrail.objects.create(
                requisition=requisition,
                user=request.user,
                role=request.user.role,
                action="rejected",
                comment=reason,
                ip_address=request.META.get("REMOTE_ADDR"),
            )

            # Update requisition status
            requisition.status = "rejected"
            requisition.next_approver = None
            requisition.save()

            messages.success(request, f"Requisition {transaction_id} rejected.")
            return redirect(
                "transactions:view_requisition", transaction_id=transaction_id
            )

        except Exception as e:
            messages.error(request, f"Error rejecting requisition: {str(e)}")

    context = {
        "requisition": requisition,
    }

    return render(request, "transactions/reject_requisition.html", context)
