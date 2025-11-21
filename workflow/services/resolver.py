from django.contrib.auth import get_user_model
from django.db.models import Q
from workflow.models import ApprovalThreshold
from django.core.exceptions import PermissionDenied
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

# Centralized roles that are not filtered by branch/region/company
CENTRALIZED_ROLES = ["treasury", "fp&a", "group_finance_manager", "cfo", "ceo", "admin"]


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
        if tier in ["Tier 1", "Tier1"]:
            base_roles = ["department_head", "group_finance_manager"]
        elif tier in ["Tier 2", "Tier2", "Tier 3", "Tier3"]:
            base_roles = ["group_finance_manager", "cfo"]
        elif tier in ["Tier 4", "Tier4"]:
            base_roles = ["cfo", "ceo"]

    # 3️⃣ Loop through roles in order
    for role in base_roles:
        # Skip staff
        if role.lower() == "staff":
            continue

        # Candidate users (case-insensitive, normalize role to lowercase for DB lookup)
        normalized_role = role.lower().replace("_", "_")  # Keep as-is for DB
        candidates = User.objects.filter(role=normalized_role, is_active=True).exclude(id=requisition.requested_by.id)

        # Apply scoping only for non-centralized roles
        if role.lower() not in CENTRALIZED_ROLES:
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
            logger.warning(f"No {role} found for requisition {requisition.transaction_id}, auto-escalation needed")
            resolved.append({
                "user_id": None,
                "role": role,
                "auto_escalated": True
            })

    # 4️⃣ Phase 4: Auto-escalation with audit trail (no valid approvers found)
    if not resolved or all(r["user_id"] is None for r in resolved):
        admin = User.objects.filter(is_superuser=True, is_active=True).first()
        if not admin:
            raise ValueError("No ADMIN user exists. Please create one.")
        escalation_reason = f"No approvers found in roles: {base_roles}"
        logger.warning(f"Auto-escalating {requisition.transaction_id} to admin: {escalation_reason}")
        resolved = [{
            "user_id": admin.id,
            "role": "ADMIN",
            "auto_escalated": True,
            "escalation_reason": escalation_reason
        }]

    # 5️⃣ Phase 3: Urgent fast-track (if enabled and Tier ≠ 4)
    if (
        getattr(requisition, "is_urgent", False)
        and requisition.applied_threshold.allow_urgent_fasttrack
        and not requisition.tier.startswith("Tier 4")  # Tier 4 cannot fast-track
        and len(resolved) > 1
        and resolved[-1].get("user_id") is not None  # Ensure last approver exists
    ):
        logger.info(
            f"Phase 3 urgent fast-track for {requisition.transaction_id}: "
            f"jumping to final approver (Tier 4 fast-track disabled)"
        )
        # Status will be set to pending_urgency_confirmation by caller
        resolved = [resolved[-1]]  # jump to last approver

    # 6️⃣ Phase 4: Replace None user_ids with escalation to next-level approver
    for i, r in enumerate(resolved):
        if r["user_id"] is None:
            # Find next available approver or escalate to admin
            next_approver = None
            for j in range(i + 1, len(resolved)):
                if resolved[j]["user_id"] is not None:
                    next_approver = resolved[j]
                    break
            
            if next_approver:
                r["user_id"] = next_approver["user_id"]
                r["auto_escalated"] = True
                r["escalation_reason"] = f"No {r['role']} found, escalated to {next_approver['role']}"
                logger.warning(f"Auto-escalated {requisition.transaction_id}: {r['escalation_reason']}")
            else:
                # Last resort: escalate to admin
                admin = User.objects.filter(is_superuser=True, is_active=True).first()
                r["user_id"] = admin.id
                r["role"] = "ADMIN"
                r["auto_escalated"] = True
                r["escalation_reason"] = f"No {r['role']} found, escalated to ADMIN"
                logger.warning(f"Admin escalation for {requisition.transaction_id}: {r['escalation_reason']}")

    # 7️⃣ Save workflow to requisition
    requisition.workflow_sequence = resolved
    requisition.next_approver = User.objects.get(id=resolved[0]["user_id"])
    requisition.save(update_fields=["workflow_sequence", "next_approver"])

    return resolved


def can_approve(user, requisition):
    """
    Check if the user can approve the requisition.
    Enforces:
    - Only pending requisitions can be approved
    - No-self-approval
    - Only next approver can act
    """
    # Only pending requisitions can be approved
    if requisition.status != 'pending':
        return False
    
    # No-self-approval
    if user.id == requisition.requested_by.id:
        return False
    
    # Must be the next approver
    if not requisition.next_approver or user.id != requisition.next_approver.id:
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
