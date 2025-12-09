from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.permissions import get_user_apps
from treasury.models import Payment

from .models import ApprovalTrail, Requisition

User = get_user_model()


# -----------------------------
# Transactions Home
# -----------------------------
@login_required
def transactions_home(request):
    # Check if user has 'transactions' app assigned
    user_apps = get_user_apps(request.user)
    if "transactions" not in user_apps:
        messages.error(request, "You don't have access to Transactions app.")
        return redirect("dashboard")

    # Check if user has permission to view requisitions
    if not request.user.has_perm("transactions.view_requisition"):
        messages.error(request, "You don't have permission to view transactions.")
        return redirect("dashboard")

    user = request.user
    is_centralized = getattr(user, "is_centralized_approver", False)

    # Define approver roles (case-insensitive)
    APPROVER_ROLES = [
        "branch_manager",
        "regional_manager",
        "department_head",
        "group_finance_manager",
        "treasury",
        "cfo",
        "admin",
        "ceo",
    ]
    is_approver = user.role.lower() in APPROVER_ROLES

    # Calculate metrics for user's own requisitions
    if is_centralized:
        my_reqs_all = Requisition.objects.filter(requested_by=user)
    else:
        my_reqs_all = Requisition.objects.current_company().filter(requested_by=user)

    my_metrics = {
        "total": my_reqs_all.count(),
        "pending": my_reqs_all.filter(
            status__in=["pending", "pending_urgency_confirmation", "change_requested"]
        ).count(),
        "approved": my_reqs_all.filter(status="approved").count(),
        "rejected": my_reqs_all.filter(status="rejected").count(),
    }

    # Calculate metrics for pending approvals (if user is approver)
    approval_metrics = {
        "pending_count": 0,
        "urgent_count": 0,
        "approved_today": 0,
    }

    if is_approver:
        if is_centralized:
            pending_approval_reqs = Requisition.objects.filter(
                status__in=["pending", "pending_urgency_confirmation"],
                next_approver=user,
            ).exclude(requested_by=user)
        else:
            pending_approval_reqs = (
                Requisition.objects.current_company()
                .filter(
                    status__in=["pending", "pending_urgency_confirmation"],
                    next_approver=user,
                )
                .exclude(requested_by=user)
            )

        approval_metrics["pending_count"] = pending_approval_reqs.count()
        approval_metrics["urgent_count"] = pending_approval_reqs.filter(
            is_urgent=True
        ).count()

        # Today's approvals
        today = timezone.now().date()
        approval_metrics["approved_today"] = ApprovalTrail.objects.filter(
            user=user, action="approved", timestamp__date=today
        ).count()

    # Treasury metrics
    treasury_metrics = {
        "ready_for_payment": 0,
        "paid_today": 0,
    }

    if user.role.lower() == "treasury":
        if is_centralized:
            ready_reqs = Requisition.objects.filter(status="reviewed")
        else:
            ready_reqs = Requisition.objects.current_company().filter(status="reviewed")

        treasury_metrics["ready_for_payment"] = ready_reqs.count()

        # Paid today
        today = timezone.now().date()
        from treasury.models import Payment

        treasury_metrics["paid_today"] = Payment.objects.filter(
            disbursed_by=user, disbursed_at__date=today, status="disbursed"
        ).count()

    context = {
        "user": user,
        "is_approver": is_approver,
        "is_centralized": is_centralized,
        "scope_label": (
            "Company-Wide"
            if is_centralized
            else (user.company.name if user.company else "Personal")
        ),
        "my_metrics": my_metrics,
        "approval_metrics": approval_metrics,
        "treasury_metrics": treasury_metrics,
    }
    return render(request, "transactions/home.html", context)


# -----------------------------
# Requisition Detail
# -----------------------------
@login_required
def requisition_detail(request, requisition_id):
    # Check if user has 'transactions' app assigned
    user_apps = get_user_apps(request.user)
    if "transactions" not in user_apps:
        messages.error(request, "You don't have access to Transactions app.")
        return redirect("dashboard")

    # Check if user has permission to view requisitions
    if not request.user.has_perm("transactions.view_requisition"):
        messages.error(request, "You don't have permission to view requisitions.")
        return redirect("dashboard")

    from treasury.models import Payment

    requisition = get_object_or_404(Requisition, transaction_id=requisition_id)
    can_act = requisition.can_approve(request.user)

    # Check if Treasury can execute payment (reviewed status)
    can_execute_payment = (
        request.user.role.lower() == "treasury" and requisition.status == "reviewed"
    )

    # Get or create payment record for reviewed requisitions
    payment = None
    if requisition.status == "reviewed":
        payment, _ = Payment.objects.get_or_create(
            requisition=requisition,
            defaults={
                "amount": requisition.amount,
                "method": "mpesa",
                "destination": "",
                "status": "pending",
                "otp_required": True,
            },
        )

    # Get approval trail with escalation details (Phase 4)
    approval_trail = (
        ApprovalTrail.objects.filter(requisition=requisition)
        .select_related("user")
        .order_by("timestamp")
    )

    context = {
        "requisition": requisition,
        "can_act": can_act,
        "can_execute_payment": can_execute_payment,
        "payment": payment,
        "user": request.user,
        "approval_trail": approval_trail,
    }
    return render(request, "transactions/requisition_detail.html", context)


# -----------------------------
# Create Requisition
# -----------------------------
@login_required
def create_requisition(request):
    # Check if user has 'transactions' app assigned
    user_apps = get_user_apps(request.user)
    if "transactions" not in user_apps:
        messages.error(request, "You don't have access to Transactions app.")
        return redirect("dashboard")

    # Check if user has permission to add requisitions
    if not request.user.has_perm("transactions.add_requisition"):
        messages.error(request, "You don't have permission to create requisitions.")
        return redirect("transactions-home")

    from .forms import RequisitionForm

    if request.method == "POST":
        form = RequisitionForm(request.POST, request.FILES)
        if form.is_valid():
            requisition = form.save(commit=False)
            requisition.requested_by = request.user

            # Phase 3: Set initial status based on urgency
            if requisition.is_urgent:
                requisition.status = "pending_urgency_confirmation"
            else:
                requisition.status = "pending"

            requisition.save()

            try:
                requisition.resolve_workflow()
            except Exception as e:
                messages.error(request, f"Error creating requisition: {str(e)}")
                requisition.delete()
                return redirect("transactions-home")

            if requisition.is_urgent:
                messages.success(
                    request,
                    f"Urgent requisition {requisition.transaction_id} created. Awaiting urgency confirmation from first approver.",
                )
            else:
                messages.success(
                    request,
                    f"Requisition {requisition.transaction_id} created successfully.",
                )
            return redirect("transactions-home")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RequisitionForm()
    return render(request, "transactions/create_requisition.html", {"form": form})


# -----------------------------
# Approve Requisition
# -----------------------------
@login_required
@transaction.atomic
def approve_requisition(request, requisition_id):
    """Approve a requisition with atomic transaction and row locking"""
    # Check if user has 'workflow' app assigned (approvers use workflow)
    user_apps = get_user_apps(request.user)
    if "workflow" not in user_apps and "transactions" not in user_apps:
        messages.error(request, "You don't have access to approve requisitions.")
        return redirect("dashboard")

    # Check if user has permission to change requisitions (approve)
    if not request.user.has_perm("transactions.change_requisition"):
        messages.error(request, "You don't have permission to approve requisitions.")
        return redirect("transactions-home")

    # Lock the row for update to prevent race conditions
    try:
        requisition = Requisition.objects.select_for_update().get(
            transaction_id=requisition_id
        )
    except Requisition.DoesNotExist:
        messages.error(request, "Requisition not found.")
        return redirect("transactions-home")

    # Validate can approve
    if not requisition.can_approve(request.user):
        return HttpResponseForbidden("You cannot approve this requisition.")

    # Create approval trail
    ApprovalTrail.objects.create(
        requisition=requisition,
        user=request.user,
        role=request.user.role,
        action="approved",
        comment=request.POST.get("comment", ""),
        timestamp=timezone.now(),
        auto_escalated=False,
        skipped_roles=getattr(requisition, "_skipped_roles", []),
    )

    # Move to next approver or mark as reviewed
    workflow_seq = requisition.workflow_sequence or []
    if len(workflow_seq) > 1:
        # More approvers remaining
        workflow_seq.pop(0)
        next_user_id = workflow_seq[0]["user_id"]
        requisition.next_approver = get_object_or_404(User, id=next_user_id)
        requisition.workflow_sequence = workflow_seq
        requisition.save(update_fields=["next_approver", "workflow_sequence"])

        # Customize message based on role
        if request.user.role.lower() == "treasury":
            messages.success(
                request,
                f"Requisition {requisition_id} validated. Moved to next approver for final approval.",
            )
        else:
            messages.success(
                request,
                f"Requisition {requisition_id} approved. Moved to next approver.",
            )
    else:
        # Final approval - mark as reviewed and create payment record for treasury
        requisition.status = "reviewed"
        requisition.next_approver = None
        requisition.workflow_sequence = []
        requisition.save(update_fields=["status", "next_approver", "workflow_sequence"])

        # Create Payment record for treasury to execute (within same transaction)
        payment, created = Payment.objects.get_or_create(
            requisition=requisition,
            defaults={
                "amount": requisition.amount,
                "method": "mpesa",  # Default to M-Pesa
                "destination": "",
                "status": "pending",
                "otp_required": True,
            },
        )

        # If approver is treasury, redirect to dashboard to execute payment
        if request.user.role.lower() == "treasury":
            messages.success(
                request,
                f"Requisition {requisition_id} validated! Please execute payment.",
            )
            return redirect(
                "dashboard"
            )  # Redirect to dashboard where pending payments are shown
        else:
            messages.success(
                request,
                f"Requisition {requisition_id} fully approved! Ready for payment.",
            )

    return redirect("transactions-home")


# -----------------------------
# Reject Requisition
# -----------------------------
@login_required
@transaction.atomic
def reject_requisition(request, requisition_id):
    """Reject a requisition with atomic transaction"""
    # Check if user has 'workflow' app assigned (approvers use workflow)
    user_apps = get_user_apps(request.user)
    if "workflow" not in user_apps and "transactions" not in user_apps:
        messages.error(request, "You don't have access to reject requisitions.")
        return redirect("dashboard")

    # Check if user has permission to change requisitions (reject)
    if not request.user.has_perm("transactions.change_requisition"):
        messages.error(request, "You don't have permission to reject requisitions.")
        return redirect("transactions-home")

    # Lock the row for update
    try:
        requisition = Requisition.objects.select_for_update().get(
            transaction_id=requisition_id
        )
    except Requisition.DoesNotExist:
        messages.error(request, "Requisition not found.")
        return redirect("transactions-home")

    # Validate status - can only reject pending requisitions
    if requisition.status != "pending":
        messages.error(request, "Can only reject pending requisitions.")
        return redirect("transactions-home")

    # Validate can reject (uses same logic as approval)
    if not requisition.can_approve(request.user):
        return HttpResponseForbidden("You cannot reject this requisition.")

    # Create rejection trail
    ApprovalTrail.objects.create(
        requisition=requisition,
        user=request.user,
        role=request.user.role,
        action="rejected",
        comment=request.POST.get("comment", ""),
        timestamp=timezone.now(),
        auto_escalated=False,
        skipped_roles=getattr(requisition, "_skipped_roles", []),
    )

    # Clear workflow and mark as rejected
    requisition.status = "rejected"
    requisition.next_approver = None
    requisition.workflow_sequence = []
    requisition.save(update_fields=["status", "next_approver", "workflow_sequence"])

    messages.success(request, f"Requisition {requisition_id} rejected.")
    return redirect("transactions-home")


@login_required
@transaction.atomic
def request_changes(request, requisition_id):
    """
    Approver requests changes from requester instead of rejecting.
    Sets deadline for response and returns requisition to requester.
    """
    from datetime import timedelta

    # Check if user has workflow app assigned
    user_apps = get_user_apps(request.user)
    if "workflow" not in user_apps and "transactions" not in user_apps:
        messages.error(request, "You don't have access to manage requisitions.")
        return redirect("dashboard")

    # Check if user has permission to change requisitions
    if not request.user.has_perm("transactions.change_requisition"):
        messages.error(request, "You don't have permission to request changes.")
        return redirect("transactions-home")

    # Lock the row for update
    try:
        requisition = Requisition.objects.select_for_update().get(
            transaction_id=requisition_id
        )
    except Requisition.DoesNotExist:
        messages.error(request, "Requisition not found.")
        return redirect("transactions-home")

    # Validate status - can only request changes on pending requisitions
    if requisition.status not in ["pending", "pending_urgency_confirmation"]:
        messages.error(request, "Can only request changes on pending requisitions.")
        return redirect("transactions-home")

    # Validate user is the next approver
    if not requisition.can_approve(request.user):
        messages.error(
            request, "You are not authorized to request changes for this requisition."
        )
        return redirect("transactions-home")

    # Get change request details
    change_details = request.POST.get("change_details", "")
    if not change_details:
        messages.error(request, "Please specify what changes are needed.")
        return redirect("requisition-detail", requisition_id=requisition_id)

    # Set deadline (48 hours from now by default)
    deadline_hours = int(request.POST.get("deadline_hours", 48))
    deadline = timezone.now() + timedelta(hours=deadline_hours)

    # Create audit trail
    ApprovalTrail.objects.create(
        requisition=requisition,
        user=request.user,
        role=request.user.role,
        action="changes_requested",
        comment=change_details,
        timestamp=timezone.now(),
    )

    # Update requisition
    requisition.status = "pending_changes"
    requisition.change_requested = True
    requisition.change_request_details = change_details
    requisition.change_requested_by = request.user
    requisition.change_request_deadline = deadline
    # Keep next_approver so it can return to same approver after changes
    requisition.save(
        update_fields=[
            "status",
            "change_requested",
            "change_request_details",
            "change_requested_by",
            "change_request_deadline",
        ]
    )

    # Send email notification to requester
    try:
        if requisition.requested_by.email:
            send_mail(
                subject=f"Action Required: Changes Requested for Requisition {requisition_id}",
                message=f"""
Dear {requisition.requested_by.get_full_name()},

The approver has requested changes to your requisition {requisition_id} (Amount: {requisition.amount}).

Requested by: {request.user.get_full_name()}
Changes Required:
{change_details}

DEADLINE: {deadline.strftime('%B %d, %Y at %I:%M %p')}

Please log in to your account and submit the requested changes before the deadline. If no response is received by the deadline, this requisition will be automatically rejected.

View and respond: [Your Transactions Dashboard]

Best regards,
Petty Cash System
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[requisition.requested_by.email],
                fail_silently=True,
            )
    except Exception:
        pass

    messages.success(
        request,
        f"Change request sent to {requisition.requested_by.get_full_name()}. "
        f"Deadline: {deadline.strftime('%B %d, %Y at %I:%M %p')}",
    )
    return redirect("transactions-home")


@login_required
@transaction.atomic
def submit_changes(request, requisition_id):
    """
    Requester submits changes in response to change request.
    Returns requisition to the approver who requested changes.
    """
    # Check if user has transactions app assigned
    user_apps = get_user_apps(request.user)
    if "transactions" not in user_apps:
        messages.error(request, "You don't have access to Transactions app.")
        return redirect("dashboard")

    # Lock the row for update
    try:
        requisition = Requisition.objects.select_for_update().get(
            transaction_id=requisition_id
        )
    except Requisition.DoesNotExist:
        messages.error(request, "Requisition not found.")
        return redirect("transactions-home")

    # Validate user is the requester
    if requisition.requested_by.id != request.user.id:
        messages.error(request, "You can only submit changes to your own requisitions.")
        return redirect("transactions-home")

    # Validate status
    if requisition.status != "pending_changes":
        messages.error(request, "This requisition is not awaiting changes.")
        return redirect("transactions-home")

    # Check if deadline passed
    if (
        requisition.change_request_deadline
        and timezone.now() > requisition.change_request_deadline
    ):
        # Auto-reject if deadline passed
        requisition.status = "rejected"
        requisition.next_approver = None
        requisition.workflow_sequence = []
        requisition.save(update_fields=["status", "next_approver", "workflow_sequence"])

        ApprovalTrail.objects.create(
            requisition=requisition,
            user=request.user,
            role=request.user.role,
            action="rejected",
            comment=f"Deadline expired: Changes not submitted by {requisition.change_request_deadline.strftime('%B %d, %Y at %I:%M %p')}",
            timestamp=timezone.now(),
        )

        messages.error(
            request,
            f"Deadline has passed. Requisition rejected. Please create a new requisition.",
        )
        return redirect("transactions-home")

    # Get response from requester
    change_response = request.POST.get("change_response", "")
    if not change_response:
        messages.error(request, "Please explain what changes you've made.")
        return redirect("requisition-detail", requisition_id=requisition_id)

    # Handle file upload (new receipt if requested)
    if "new_receipt" in request.FILES:
        requisition.receipt = request.FILES["new_receipt"]

    # Handle amount update if provided
    new_amount = request.POST.get("new_amount")
    if new_amount:
        try:
            requisition.amount = float(new_amount)
        except ValueError:
            messages.error(request, "Invalid amount provided.")
            return redirect("requisition-detail", requisition_id=requisition_id)

    # Create audit trail
    ApprovalTrail.objects.create(
        requisition=requisition,
        user=request.user,
        role=request.user.role,
        action="changes_submitted",
        comment=change_response,
        timestamp=timezone.now(),
    )

    # Return to pending and same approver
    requisition.status = "pending"
    requisition.change_requested = False
    requisition.save(update_fields=["status", "change_requested", "receipt", "amount"])

    # Notify approver
    try:
        if requisition.change_requested_by and requisition.change_requested_by.email:
            send_mail(
                subject=f"Changes Submitted: Requisition {requisition_id}",
                message=f"""
Dear {requisition.change_requested_by.get_full_name()},

{requisition.requested_by.get_full_name()} has submitted the changes you requested for requisition {requisition_id}.

Requester's Response:
{change_response}

The requisition is now back in your queue for review. Please log in to approve or request additional changes.

Best regards,
Petty Cash System
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[requisition.change_requested_by.email],
                fail_silently=True,
            )
    except Exception:
        pass

    messages.success(
        request,
        f"Changes submitted successfully! Requisition returned to {requisition.next_approver.get_full_name()} for review.",
    )
    return redirect("transactions-home")


@login_required
@transaction.atomic
def revert_fast_track(request, requisition_id):
    """
    Revert a fast-tracked requisition to normal approval flow.
    Only available to the final approver when reviewing a fast-tracked requisition.
    """
    # Check if user has workflow app assigned
    user_apps = get_user_apps(request.user)
    if "workflow" not in user_apps and "transactions" not in user_apps:
        messages.error(request, "You don't have access to manage requisitions.")
        return redirect("dashboard")

    # Check if user has permission to change requisitions
    if not request.user.has_perm("transactions.change_requisition"):
        messages.error(
            request, "You don't have permission to revert fast-tracked requisitions."
        )
        return redirect("transactions-home")

    # Lock the row for update
    try:
        requisition = Requisition.objects.select_for_update().get(
            transaction_id=requisition_id
        )
    except Requisition.DoesNotExist:
        messages.error(request, "Requisition not found.")
        return redirect("transactions-home")

    # Validate requisition is fast-tracked
    if not requisition.is_fast_tracked:
        messages.error(request, "This requisition was not fast-tracked.")
        return redirect("transactions-home")

    # Validate status - can only revert pending requisitions
    if requisition.status != "pending":
        messages.error(request, "Can only revert pending fast-tracked requisitions.")
        return redirect("transactions-home")

    # Validate user is the next approver (final approver in fast-track)
    if not requisition.can_approve(request.user):
        messages.error(request, "You are not authorized to revert this requisition.")
        return redirect("transactions-home")

    # Restore original workflow sequence
    if not requisition.original_workflow_sequence:
        messages.error(request, "Original workflow sequence not found.")
        return redirect("transactions-home")

    # Create audit trail for reversion
    revert_reason = request.POST.get(
        "revert_reason", "Urgency not validated - reverting to normal approval flow"
    )
    ApprovalTrail.objects.create(
        requisition=requisition,
        user=request.user,
        role=request.user.role,
        action="reverted_to_normal",
        comment=revert_reason,
        timestamp=timezone.now(),
        auto_escalated=False,
    )

    # Restore original workflow and reset to first approver
    requisition.workflow_sequence = requisition.original_workflow_sequence.copy()
    requisition.is_fast_tracked = False

    # Find the first approver in the original sequence
    if requisition.workflow_sequence:
        first_approver_role = requisition.workflow_sequence[0]
        # Find user with this role (simplified - in production, use proper role-to-user resolver)
        first_approver = User.objects.filter(role=first_approver_role).first()
        if first_approver:
            requisition.next_approver = first_approver
        else:
            messages.warning(
                request,
                f"Could not find user with role '{first_approver_role}'. Please assign manually.",
            )
            requisition.next_approver = None

    requisition.save(
        update_fields=["workflow_sequence", "is_fast_tracked", "next_approver"]
    )

    # Send email notification to requester
    try:
        if requisition.requested_by.email:
            send_mail(
                subject=f"Requisition {requisition_id} - Fast-Track Reverted",
                message=f"""
Dear {requisition.requested_by.get_full_name()},

Your requisition {requisition_id} (Amount: {requisition.amount}) was fast-tracked but has been REVERTED to normal approval flow.

Reverted by: {request.user.get_full_name()}
Reason: {revert_reason}

Your requisition will now go through all required approvers in the normal approval sequence.
Next Approver: {requisition.next_approver.get_full_name() if requisition.next_approver else 'Pending assignment'}

You can view the full details and approval trail in your Transactions dashboard.

Best regards,
Petty Cash System
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[requisition.requested_by.email],
                fail_silently=True,
            )
    except Exception as e:
        # Don't fail the revert if email fails
        pass

    messages.success(
        request,
        f"Requisition {requisition_id} reverted to normal approval flow. "
        f"It will now go through all required approvers starting from {requisition.next_approver.get_full_name() if requisition.next_approver else 'first approver'}. "
        f"Requester has been notified via email.",
    )
    return redirect("transactions-home")


# -----------------------------
# Phase 4: Admin Override (Emergency Approval)
# -----------------------------
@login_required
@transaction.atomic
def admin_override_approval(request, requisition_id):
    """
    Phase 4: Admin override to force-approve a requisition in emergency situations.

    Requirements:
    - User must have transactions.change_requisition permission
    - User must be superuser or admin role
    - Justification is REQUIRED
    - Logged with override=True in ApprovalTrail
    - Bypasses normal can_approve() checks
    """
    # Check Django permission first
    if not request.user.has_perm("transactions.change_requisition"):
        return HttpResponseForbidden("You don't have permission to override approvals.")

    # Additional role check: Only superusers or admin role can override
    if not (request.user.is_superuser or request.user.role.lower() == "admin"):
        return HttpResponseForbidden("Only administrators can override approvals.")

    # Lock the row for update
    try:
        requisition = Requisition.objects.select_for_update().get(
            transaction_id=requisition_id
        )
    except Requisition.DoesNotExist:
        messages.error(request, "Requisition not found.")
        return redirect("transactions-home")

    # Validate status - cannot override already approved/rejected requisitions
    if requisition.status in ["reviewed", "paid", "rejected"]:
        messages.error(
            request, f"Cannot override requisition with status: {requisition.status}"
        )
        return redirect("transactions-home")

    # Justification is REQUIRED for override
    justification = request.POST.get("justification", "").strip()
    if not justification:
        messages.error(request, "Justification is required for admin override.")
        return redirect("requisition-detail", requisition_id=requisition_id)

    # Create override trail entry
    ApprovalTrail.objects.create(
        requisition=requisition,
        user=request.user,
        role=request.user.role,
        action="approved",
        comment=f"ADMIN OVERRIDE: {justification}",
        timestamp=timezone.now(),
        auto_escalated=False,
        override=True,  # Mark as override
    )

    # Force approve - mark as reviewed
    requisition.status = "reviewed"
    requisition.next_approver = None
    requisition.workflow_sequence = []
    requisition.save(update_fields=["status", "next_approver", "workflow_sequence"])

    # Create Payment record for treasury to execute
    Payment.objects.get_or_create(
        requisition=requisition,
        defaults={
            "amount": requisition.amount,
            "method": "bank_transfer",
            "destination": "",
            "status": "pending",
            "otp_required": True,
        },
    )

    messages.warning(
        request,
        f"⚠️ ADMIN OVERRIDE: Requisition {requisition_id} force-approved. "
        f"This action has been logged for audit.",
    )

    return redirect("transactions-home")


# -----------------------------
# Phase 3: Confirm Urgency (First Approver)
# -----------------------------
@login_required
@transaction.atomic
def confirm_urgency(request, requisition_id):
    """
    Phase 3: First approver confirms or denies urgency claim.

    If confirmed: Apply fast-track logic (skip to final approver if allowed)
    If denied: Follow normal workflow (no fast-track)

    Requires: transactions.change_requisition permission
    """
    # Check if user has 'workflow' app assigned (approvers use workflow)
    user_apps = get_user_apps(request.user)
    if "workflow" not in user_apps and "transactions" not in user_apps:
        messages.error(request, "You don't have access to confirm urgency.")
        return redirect("dashboard")

    # Check if user has permission to change requisitions
    if not request.user.has_perm("transactions.change_requisition"):
        messages.error(request, "You don't have permission to confirm urgency.")
        return redirect("transactions-home")

    # Lock the row for update
    try:
        requisition = Requisition.objects.select_for_update().get(
            transaction_id=requisition_id
        )
    except Requisition.DoesNotExist:
        messages.error(request, "Requisition not found.")
        return redirect("transactions-home")

    # Validate status - must be pending_urgency_confirmation
    if requisition.status != "pending_urgency_confirmation":
        messages.error(
            request, "This requisition is not awaiting urgency confirmation."
        )
        return redirect("transactions-home")

    # Validate user is the next approver
    if not requisition.next_approver or request.user.id != requisition.next_approver.id:
        return HttpResponseForbidden("Only the first approver can confirm urgency.")

    # Get action from POST (confirm or deny)
    action = request.POST.get("action")
    comment = request.POST.get("comment", "")

    if action == "confirm":
        # Create urgency_confirmed trail entry
        ApprovalTrail.objects.create(
            requisition=requisition,
            user=request.user,
            role=request.user.role,
            action="urgency_confirmed",
            comment=comment or "Urgency confirmed by first approver",
            timestamp=timezone.now(),
            auto_escalated=False,
        )

        # Apply fast-track if allowed for this tier
        if (
            requisition.applied_threshold
            and requisition.applied_threshold.allow_urgent_fasttrack
            and not requisition.tier.startswith("Tier 4")
        ):

            # Fast-track: Jump to final approver
            workflow_seq = requisition.workflow_sequence or []
            if len(workflow_seq) > 1:
                final_approver = workflow_seq[-1]
                requisition.workflow_sequence = [final_approver]
                requisition.next_approver = get_object_or_404(
                    User, id=final_approver["user_id"]
                )
                requisition.status = "pending"
                requisition.save(
                    update_fields=["workflow_sequence", "next_approver", "status"]
                )
                messages.success(
                    request,
                    f"Urgency confirmed! Fast-tracked to final approver: {requisition.next_approver.username}",
                )
            else:
                # Only one approver - mark as reviewed
                requisition.status = "reviewed"
                requisition.next_approver = None
                requisition.workflow_sequence = []
                requisition.save(
                    update_fields=["status", "next_approver", "workflow_sequence"]
                )
                messages.success(request, "Urgency confirmed! Requisition approved.")
        else:
            # Tier 4 or fast-track not allowed - follow normal workflow
            requisition.status = "pending"
            requisition.save(update_fields=["status"])
            messages.success(
                request,
                f"Urgency confirmed! Following normal approval workflow (Tier 4 or fast-track disabled).",
            )

    elif action == "deny":
        # Deny urgency - create rejection trail entry
        ApprovalTrail.objects.create(
            requisition=requisition,
            user=request.user,
            role=request.user.role,
            action="rejected",
            comment=comment or "Urgency claim denied - requisition rejected",
            timestamp=timezone.now(),
            auto_escalated=False,
        )

        # Reject the requisition
        requisition.status = "rejected"
        requisition.next_approver = None
        requisition.workflow_sequence = []
        requisition.save(update_fields=["status", "next_approver", "workflow_sequence"])
        messages.success(
            request, f"Urgency denied. Requisition {requisition_id} rejected."
        )

    else:
        messages.error(request, "Invalid action. Please confirm or deny urgency.")

    return redirect("transactions-home")


# -----------------------------
# My Requisitions (Separate View for Approvers)
# -----------------------------
@login_required
def my_requisitions(request):
    """
    Dedicated view for user's own requisitions (separate from approval queue).
    Shows requisitions created by the logged-in user with their own metrics.
    """
    # Check if user has 'transactions' app assigned
    user_apps = get_user_apps(request.user)
    if "transactions" not in user_apps:
        messages.error(request, "You don't have access to Transactions app.")
        return redirect("dashboard")

    # Check if user has permission to view requisitions
    if not request.user.has_perm("transactions.view_requisition"):
        messages.error(request, "You don't have permission to view requisitions.")
        return redirect("dashboard")

    user = request.user
    is_centralized = getattr(user, "is_centralized_approver", False)

    # Get user's own requisitions
    if is_centralized:
        requisitions = (
            Requisition.objects.filter(requested_by=user)
            .select_related("next_approver", "requested_by__company")
            .prefetch_related("approvaltrail_set")
            .order_by("-created_at")
        )
    else:
        requisitions = (
            Requisition.objects.current_company()
            .filter(requested_by=user)
            .select_related("next_approver")
            .prefetch_related("approvaltrail_set")
            .order_by("-created_at")
        )

    # Apply filters
    status_filter = request.GET.get("status", "")
    search_query = request.GET.get("search", "")

    if status_filter:
        requisitions = requisitions.filter(status=status_filter)

    if search_query:
        requisitions = requisitions.filter(
            transaction_id__icontains=search_query
        ) | requisitions.filter(description__icontains=search_query)

    # Calculate metrics for user's own requisitions
    all_my_reqs = (
        Requisition.objects.filter(requested_by=user)
        if is_centralized
        else Requisition.objects.current_company().filter(requested_by=user)
    )

    metrics = {
        "total": all_my_reqs.count(),
        "pending": all_my_reqs.filter(
            status__in=["pending", "pending_urgency_confirmation", "change_requested"]
        ).count(),
        "approved": all_my_reqs.filter(status="approved").count(),
        "reviewed": all_my_reqs.filter(status="reviewed").count(),
        "paid": all_my_reqs.filter(status="paid").count(),
        "rejected": all_my_reqs.filter(status="rejected").count(),
        "total_amount": sum(r.amount for r in all_my_reqs),
        "pending_amount": sum(
            r.amount
            for r in all_my_reqs.filter(
                status__in=["pending", "pending_urgency_confirmation"]
            )
        ),
    }

    context = {
        "requisitions": requisitions,
        "metrics": metrics,
        "status_filter": status_filter,
        "search_query": search_query,
        "is_centralized": is_centralized,
        "scope_label": (
            "Company-Wide"
            if is_centralized
            else (user.company.name if user.company else "Personal")
        ),
    }
    return render(request, "transactions/my_requisitions.html", context)


# -----------------------------
# Pending Approvals (Separate View for Approvers)
# -----------------------------
@login_required
def pending_approvals(request):
    """
    Dedicated view for requisitions awaiting approval by the logged-in user.
    Shows only requisitions submitted by OTHERS that require user's approval.
    """
    # Check if user has 'transactions' app assigned
    user_apps = get_user_apps(request.user)
    if "transactions" not in user_apps:
        messages.error(request, "You don't have access to Transactions app.")
        return redirect("dashboard")

    # Check if user has permission to approve requisitions
    if not request.user.has_perm("transactions.change_requisition"):
        messages.error(request, "You don't have permission to approve requisitions.")
        return redirect("dashboard")

    user = request.user
    is_centralized = getattr(user, "is_centralized_approver", False)

    # Define approver roles
    APPROVER_ROLES = [
        "branch_manager",
        "regional_manager",
        "department_head",
        "group_finance_manager",
        "treasury",
        "cfo",
        "admin",
        "ceo",
    ]

    if user.role.lower() not in APPROVER_ROLES:
        messages.error(request, "You don't have an approver role.")
        return redirect("transactions-home")

    # Get requisitions awaiting THIS user's approval (exclude own requisitions)
    if is_centralized:
        requisitions = (
            Requisition.objects.filter(
                status__in=["pending", "pending_urgency_confirmation"],
                next_approver=user,
            )
            .exclude(requested_by=user)
            .select_related("requested_by", "requested_by__company", "next_approver")
            .prefetch_related("approvaltrail_set")
            .order_by("-created_at")
        )
    else:
        requisitions = (
            Requisition.objects.current_company()
            .filter(
                status__in=["pending", "pending_urgency_confirmation"],
                next_approver=user,
            )
            .exclude(requested_by=user)
            .select_related("requested_by", "next_approver")
            .prefetch_related("approvaltrail_set")
            .order_by("-created_at")
        )

    # Apply filters
    urgency_filter = request.GET.get("urgency", "")
    amount_filter = request.GET.get("amount", "")
    search_query = request.GET.get("search", "")

    if urgency_filter == "urgent":
        requisitions = requisitions.filter(is_urgent=True)
    elif urgency_filter == "normal":
        requisitions = requisitions.filter(is_urgent=False)

    if amount_filter == "high":
        requisitions = requisitions.filter(amount__gte=100000)
    elif amount_filter == "medium":
        requisitions = requisitions.filter(amount__gte=10000, amount__lt=100000)
    elif amount_filter == "low":
        requisitions = requisitions.filter(amount__lt=10000)

    if search_query:
        requisitions = (
            requisitions.filter(transaction_id__icontains=search_query)
            | requisitions.filter(description__icontains=search_query)
            | requisitions.filter(requested_by__username__icontains=search_query)
        )

    # Calculate metrics for approval queue
    all_pending = Requisition.objects.filter(
        next_approver=user, status__in=["pending", "pending_urgency_confirmation"]
    ).exclude(requested_by=user)

    if not is_centralized:
        all_pending = all_pending.filter(requested_by__company=user.company)

    # Today's approvals by this user
    today = timezone.now().date()
    approved_today = ApprovalTrail.objects.filter(
        user=user, action="approved", timestamp__date=today
    ).count()

    rejected_today = ApprovalTrail.objects.filter(
        user=user, action="rejected", timestamp__date=today
    ).count()

    metrics = {
        "pending_count": all_pending.count(),
        "urgent_count": all_pending.filter(is_urgent=True).count(),
        "total_pending_amount": sum(r.amount for r in all_pending),
        "approved_today": approved_today,
        "rejected_today": rejected_today,
        "pending_urgency_confirmation": all_pending.filter(
            status="pending_urgency_confirmation"
        ).count(),
    }

    context = {
        "requisitions": requisitions,
        "metrics": metrics,
        "urgency_filter": urgency_filter,
        "amount_filter": amount_filter,
        "search_query": search_query,
        "is_centralized": is_centralized,
        "scope_label": (
            "Company-Wide"
            if is_centralized
            else (user.company.name if user.company else "Personal")
        ),
    }
    return render(request, "transactions/pending_approvals.html", context)
