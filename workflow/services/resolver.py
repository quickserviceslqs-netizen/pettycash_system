from django.contrib.auth import get_user_model
from django.db.models import Q
from workflow.models import ApprovalThreshold
from django.core.exceptions import PermissionDenied

User = get_user_model()


def find_approval_threshold(amount, origin_type):
    """
    Find a matching ApprovalThreshold for the requisition.
    """
    thresholds = (
        ApprovalThreshold.objects.filter(is_active=True)
        .filter(Q(origin_type=origin_type.upper()) | Q(origin_type='ANY'))
        .order_by('priority', 'min_amount')
    )

    for thr in thresholds:
        if thr.min_amount <= amount <= thr.max_amount:
            return thr
    return None


def resolve_workflow(requisition):
    """
    Build approval workflow based on threshold, origin, urgency, and requester role.
    Handles:
    - Case-insensitive role matching
    - Centralized roles
    - Scoped routing
    - No-self-approval
    - Treasury-originated overrides
    - Urgent fast-track
    """
    # 1️⃣ Load threshold if not already applied
    if not requisition.applied_threshold:
        thr = find_approval_threshold(requisition.amount, requisition.origin_type)
        if not thr:
            raise ValueError("No ApprovalThreshold found for this requisition.")

        requisition.applied_threshold = thr
        requisition.tier = thr.name
        requisition.save(update_fields=["applied_threshold", "tier"])

    base_roles = requisition.applied_threshold.roles_sequence  # e.g., ["BRANCH_MANAGER","TREASURY"]
    resolved = []

    # 2️⃣ Treasury special case override
    is_treasury_request = requisition.requested_by.role.lower() == "treasury"
    if is_treasury_request:
        tier = requisition.tier
        if tier == "Tier1":
            base_roles = ["DEPT_HEAD", "GROUP_FINANCE_MANAGER"]
        elif tier in ["Tier2", "Tier3"]:
            base_roles = ["GROUP_FINANCE_MANAGER", "CFO"]
        elif tier == "Tier4":
            base_roles = ["CFO", "CEO"]

    # 3️⃣ Loop through roles in order
    for role in base_roles:
        # Skip staff
        if role.lower() == "staff":
            continue

        # Candidate users (case-insensitive)
        candidates = User.objects.filter(role__iexact=role, is_active=True).exclude(id=requisition.requested_by.id)

        # Apply scoping only for non-centralized roles
        centralized_roles = ["TREASURY", "FPNA", "GROUP_FINANCE_MANAGER", "CFO", "CEO", "ADMIN"]
        if role.upper() not in centralized_roles:
            if requisition.origin_type.lower() == "branch" and requisition.branch:
                candidates = candidates.filter(branch=requisition.branch)
            elif requisition.origin_type.lower() == "hq" and requisition.company:
                candidates = candidates.filter(company=requisition.company)
            elif requisition.origin_type.lower() == "field" and requisition.region:
                candidates = candidates.filter(region=requisition.region)

        candidate = candidates.first()
        if candidate:
            resolved.append({
                "user_id": candidate.id,
                "role": role,
                "auto_escalated": False
            })
        else:
            # Auto-escalation flag if no candidate
            resolved.append({
                "user_id": None,
                "role": role,
                "auto_escalated": True
            })

    # 4️⃣ Fallback: assign Admin if no valid approvers
    if not resolved or all(r["user_id"] is None for r in resolved):
        admin = User.objects.filter(is_superuser=True, is_active=True).first()
        if not admin:
            raise ValueError("No ADMIN user exists. Please create one.")
        resolved = [{
            "user_id": admin.id,
            "role": "ADMIN",
            "auto_escalated": True
        }]

    # 5️⃣ Urgent fast-track
    if (
        getattr(requisition, "is_urgent", False)
        and requisition.applied_threshold.allow_urgent_fasttrack
        and requisition.tier != "Tier4"
        and len(resolved) > 1
    ):
        resolved = [resolved[-1]]  # jump to last approver

    # 6️⃣ Replace None user_ids with Admin if still missing
    for r in resolved:
        if r["user_id"] is None:
            admin = User.objects.filter(is_superuser=True, is_active=True).first()
            r["user_id"] = admin.id
            r["role"] = "ADMIN"

    # 7️⃣ Save workflow to requisition
    requisition.workflow_sequence = resolved
    requisition.next_approver = User.objects.get(id=resolved[0]["user_id"])
    requisition.save(update_fields=["workflow_sequence", "next_approver"])

    return resolved


def can_approve(user, requisition):
    """
    Check if the user can approve the requisition.
    Enforces:
    - No-self-approval
    - Only next approver can act
    """
    if user.id == requisition.requested_by.id:
        return False
    if user.id != requisition.next_approver.id:
        return False
    return True


def execute_payment(payment, executor_user):
    """
    Execute payment.
    Enforces:
    - Executor cannot be the original requester
    - Treasury self-request rules
    """
    if executor_user.id == payment.requisition.requested_by.id:
        raise PermissionDenied("Executor cannot be the original requester.")
    # Proceed with payment logic...
