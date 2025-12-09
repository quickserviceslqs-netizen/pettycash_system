import json

from transactions.models import ApprovalThreshold, User


def get_tier(amount):
    """Determine tier based on amount."""
    thresholds = ApprovalThreshold.objects.all()
    for t in thresholds:
        if t.min_amount <= amount <= t.max_amount:
            return t
    return None


def resolve_workflow_sequence(requisition):
    """
    Generate the approval workflow for a requisition:
    - Uses origin_type, tier, urgency
    - Excludes requester
    - Handles escalation
    """
    tier_obj = get_tier(requisition.amount)
    if not tier_obj:
        raise ValueError("No tier matches this amount")

    roles_sequence = tier_obj.roles_sequence  # list of roles
    resolved = []

    for role in roles_sequence:
        # Find available user in scope
        candidates = User.objects.filter(role=role)
        # Apply origin/branch/department filters
        if requisition.origin_type == "Branch":
            candidates = candidates.filter(branch=requisition.branch)
        elif requisition.origin_type == "HQ":
            candidates = candidates.filter(company=requisition.company)
        # Exclude requester
        candidates = candidates.exclude(id=requisition.requested_by.id)
        if candidates.exists():
            resolved.append(
                {
                    "user_id": candidates.first().id,
                    "role": role,
                    "auto_escalated": False,
                }
            )
        else:
            # Auto escalate to admin if no candidate
            admin = User.objects.filter(role="ADMIN").first()
            resolved.append(
                {"user_id": admin.id, "role": "ADMIN", "auto_escalated": True}
            )

    # Handle urgency fast-track if allowed
    if (
        requisition.is_urgent
        and tier_obj.allow_urgent_fasttrack
        and requisition.tier != 4
    ):
        # Simplified: fast-track to last approver in list (can be customized)
        resolved = [resolved[-1]]

    requisition.workflow_sequence = resolved
    requisition.next_approver_id = resolved[0]["user_id"]
    requisition.save()
    return resolved
