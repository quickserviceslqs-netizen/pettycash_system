from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.utils import timezone

from .models import Requisition, ApprovalTrail
from django.contrib.auth import get_user_model
User = get_user_model()


# -----------------------------
# Transactions Home
# -----------------------------
@login_required
def transactions_home(request):
    user = request.user

    # Define approver roles (case-insensitive)
    # Note: application role 'staff' is NOT an approver by design.
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

    my_requisitions = Requisition.objects.filter(requested_by=user).order_by('-created_at')

    if is_approver:
        pending_for_me = Requisition.objects.filter(
            status="pending",
            next_approver=user
        ).exclude(requested_by=user).order_by('-created_at')
        show_pending_section = pending_for_me.exists()
    else:
        pending_for_me = Requisition.objects.none()
        show_pending_section = False

    context = {
        "user": user,
        "is_approver": is_approver,
        "requisitions": my_requisitions,
        "pending_for_me": pending_for_me,
        "show_pending_section": show_pending_section,
    }
    return render(request, "transactions/home.html", context)


# -----------------------------
# Requisition Detail
# -----------------------------
@login_required
def requisition_detail(request, requisition_id):
    requisition = get_object_or_404(Requisition, transaction_id=requisition_id)
    can_act = requisition.can_approve(request.user)
    return render(request, "transactions/requisition_detail.html", {"requisition": requisition, "can_act": can_act, "user": request.user})


# -----------------------------
# Create Requisition
# -----------------------------
@login_required
def create_requisition(request):
    from .forms import RequisitionForm

    if request.method == "POST":
        form = RequisitionForm(request.POST)
        if form.is_valid():
            requisition = form.save(commit=False)
            requisition.requested_by = request.user
            requisition.status = "pending"
            requisition.save()

            try:
                requisition.resolve_workflow()
            except Exception as e:
                messages.error(request, f"Error creating requisition: {str(e)}")
                requisition.delete()
                return redirect("transactions-home")

            messages.success(request, f"Requisition {requisition.transaction_id} created successfully.")
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
def approve_requisition(request, requisition_id):
    requisition = get_object_or_404(Requisition, transaction_id=requisition_id)
    if not requisition.can_approve(request.user):
        return HttpResponseForbidden("You cannot approve this requisition.")

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

    # Move to next approver
    workflow_seq = requisition.workflow_sequence or []
    if len(workflow_seq) > 1:
        workflow_seq.pop(0)
        next_user_id = workflow_seq[0]["user_id"]
        requisition.next_approver = get_object_or_404(User, id=next_user_id)
        requisition.workflow_sequence = workflow_seq
        requisition.save(update_fields=["next_approver", "workflow_sequence"])
    else:
        requisition.status = "reviewed"
        requisition.next_approver = None
        requisition.workflow_sequence = []
        requisition.save(update_fields=["status", "next_approver", "workflow_sequence"])

    messages.success(request, f"Requisition {requisition_id} approved successfully.")
    return redirect("transactions-home")


# -----------------------------
# Reject Requisition
# -----------------------------
@login_required
def reject_requisition(request, requisition_id):
    requisition = get_object_or_404(Requisition, transaction_id=requisition_id)
    if not requisition.can_approve(request.user):
        return HttpResponseForbidden("You cannot reject this requisition.")

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

    requisition.status = "rejected"
    requisition.next_approver = None
    requisition.workflow_sequence = []
    requisition.save(update_fields=["status", "next_approver", "workflow_sequence"])
    messages.success(request, f"Requisition {requisition_id} rejected.")
    return redirect("transactions-home")
