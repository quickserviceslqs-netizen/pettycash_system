from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.utils import timezone
from django.db import transaction

from .models import Requisition, ApprovalTrail
from treasury.models import Payment
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

    # Multi-Tenancy: Filter requisitions by user's company
    my_requisitions = Requisition.objects.current_company().filter(
        requested_by=user
    ).order_by('-created_at')

    # Treasury sees reviewed requisitions ready for payment
    if user.role.lower() == 'treasury':
        ready_for_payment = Requisition.objects.current_company().filter(
            status="reviewed"
        ).select_related('requested_by').order_by('-created_at')
        show_payment_section = ready_for_payment.exists()
        pending_for_me = Requisition.objects.none()
        show_pending_section = False
    elif is_approver:
        # Other approvers see pending approvals (within their company)
        pending_for_me = Requisition.objects.current_company().filter(
            status__in=["pending", "pending_urgency_confirmation"],
            next_approver=user
        ).exclude(requested_by=user).order_by('-created_at')
        show_pending_section = pending_for_me.exists()
        ready_for_payment = Requisition.objects.none()
        show_payment_section = False
    else:
        pending_for_me = Requisition.objects.none()
        show_pending_section = False
        ready_for_payment = Requisition.objects.none()
        show_payment_section = False

    context = {
        "user": user,
        "is_approver": is_approver,
        "requisitions": my_requisitions,
        "pending_for_me": pending_for_me,
        "show_pending_section": show_pending_section,
        "ready_for_payment": ready_for_payment,
        "show_payment_section": show_payment_section,
    }
    return render(request, "transactions/home.html", context)


# -----------------------------
# Requisition Detail
# -----------------------------
@login_required
def requisition_detail(request, requisition_id):
    from treasury.models import Payment
    
    requisition = get_object_or_404(Requisition, transaction_id=requisition_id)
    can_act = requisition.can_approve(request.user)
    
    # Check if Treasury can execute payment (reviewed status)
    can_execute_payment = (
        request.user.role.lower() == 'treasury' and 
        requisition.status == 'reviewed'
    )
    
    # Get or create payment record for reviewed requisitions
    payment = None
    if requisition.status == 'reviewed':
        payment, _ = Payment.objects.get_or_create(
            requisition=requisition,
            defaults={
                'amount': requisition.amount,
                'method': 'mpesa',
                'destination': '',
                'status': 'pending',
                'otp_required': True,
            }
        )
    
    # Get approval trail with escalation details (Phase 4)
    approval_trail = ApprovalTrail.objects.filter(
        requisition=requisition
    ).select_related('user').order_by('timestamp')
    
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
                messages.success(request, f"Urgent requisition {requisition.transaction_id} created. Awaiting urgency confirmation from first approver.")
            else:
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
@transaction.atomic
def approve_requisition(request, requisition_id):
    """Approve a requisition with atomic transaction and row locking"""
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
        if request.user.role.lower() == 'treasury':
            messages.success(request, f"Requisition {requisition_id} validated. Moved to next approver for final approval.")
        else:
            messages.success(request, f"Requisition {requisition_id} approved. Moved to next approver.")
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
                'amount': requisition.amount,
                'method': 'mpesa',  # Default to M-Pesa
                'destination': '',
                'status': 'pending',
                'otp_required': True,
            }
        )
        
        # If approver is treasury, redirect to dashboard to execute payment
        if request.user.role.lower() == 'treasury':
            messages.success(request, f"Requisition {requisition_id} validated! Please execute payment.")
            return redirect('dashboard')  # Redirect to dashboard where pending payments are shown
        else:
            messages.success(request, f"Requisition {requisition_id} fully approved! Ready for payment.")

    return redirect("transactions-home")


# -----------------------------
# Reject Requisition
# -----------------------------
@login_required
@transaction.atomic
def reject_requisition(request, requisition_id):
    """Reject a requisition with atomic transaction"""
    # Lock the row for update
    try:
        requisition = Requisition.objects.select_for_update().get(
            transaction_id=requisition_id
        )
    except Requisition.DoesNotExist:
        messages.error(request, "Requisition not found.")
        return redirect("transactions-home")
    
    # Validate status - can only reject pending requisitions
    if requisition.status != 'pending':
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


# -----------------------------
# Phase 4: Admin Override (Emergency Approval)
# -----------------------------
@login_required
@transaction.atomic
def admin_override_approval(request, requisition_id):
    """
    Phase 4: Admin override to force-approve a requisition in emergency situations.
    
    Requirements:
    - User must be superuser or admin role
    - Justification is REQUIRED
    - Logged with override=True in ApprovalTrail
    - Bypasses normal can_approve() checks
    """
    # Only superusers or admin role can override
    if not (request.user.is_superuser or request.user.role.lower() == 'admin'):
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
    if requisition.status in ['reviewed', 'paid', 'rejected']:
        messages.error(request, f"Cannot override requisition with status: {requisition.status}")
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
            'amount': requisition.amount,
            'method': 'bank_transfer',
            'destination': '',
            'status': 'pending',
            'otp_required': True,
        }
    )
    
    messages.warning(
        request, 
        f"⚠️ ADMIN OVERRIDE: Requisition {requisition_id} force-approved. "
        f"This action has been logged for audit."
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
    """
    # Lock the row for update
    try:
        requisition = Requisition.objects.select_for_update().get(
            transaction_id=requisition_id
        )
    except Requisition.DoesNotExist:
        messages.error(request, "Requisition not found.")
        return redirect("transactions-home")
    
    # Validate status - must be pending_urgency_confirmation
    if requisition.status != 'pending_urgency_confirmation':
        messages.error(request, "This requisition is not awaiting urgency confirmation.")
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
        if (requisition.applied_threshold 
            and requisition.applied_threshold.allow_urgent_fasttrack
            and not requisition.tier.startswith("Tier 4")):
            
            # Fast-track: Jump to final approver
            workflow_seq = requisition.workflow_sequence or []
            if len(workflow_seq) > 1:
                final_approver = workflow_seq[-1]
                requisition.workflow_sequence = [final_approver]
                requisition.next_approver = get_object_or_404(User, id=final_approver["user_id"])
                requisition.status = "pending"
                requisition.save(update_fields=["workflow_sequence", "next_approver", "status"])
                messages.success(request, f"Urgency confirmed! Fast-tracked to final approver: {requisition.next_approver.username}")
            else:
                # Only one approver - mark as reviewed
                requisition.status = "reviewed"
                requisition.next_approver = None
                requisition.workflow_sequence = []
                requisition.save(update_fields=["status", "next_approver", "workflow_sequence"])
                messages.success(request, "Urgency confirmed! Requisition approved.")
        else:
            # Tier 4 or fast-track not allowed - follow normal workflow
            requisition.status = "pending"
            requisition.save(update_fields=["status"])
            messages.success(request, f"Urgency confirmed! Following normal approval workflow (Tier 4 or fast-track disabled).")
        
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
        messages.success(request, f"Urgency denied. Requisition {requisition_id} rejected.")
    
    else:
        messages.error(request, "Invalid action. Please confirm or deny urgency.")
    
    return redirect("transactions-home")
