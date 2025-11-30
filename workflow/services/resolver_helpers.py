from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from settings_manager.models import get_setting

User = get_user_model()

# Reuse centralized roles constant from resolver to keep behavior consistent
CENTRALIZED_ROLES = ["treasury", "fp&a", "group_finance_manager", "cfo", "ceo", "admin"]


def build_base_roles(requisition, allow_self_approval=True):
    """Return the base roles list for a requisition, excluding 'treasury'.

    This function mirrors the threshold/treasury overrides and removes treasury
    from stored sequences to ensure validators aren't treated as approvers.
    """
    from workflow.services.resolver import find_approval_threshold

    if not requisition.applied_threshold:
        thr = find_approval_threshold(requisition.amount, requisition.origin_type)
        if not thr:
            raise ValueError("No ApprovalThreshold found for this requisition.")
        requisition.applied_threshold = thr
        requisition.tier = thr.name
        requisition.save(update_fields=["applied_threshold", "tier"])

    base_roles = list(requisition.applied_threshold.roles_sequence or [])

    # Ensure Treasury is not part of approval chain
    try:
        base_roles = [r for r in base_roles if str(r).strip().lower() != 'treasury']
    except Exception:
        base_roles = list(base_roles)

    # Treasury-originated special-case: override some tiers
    is_treasury_request = getattr(requisition.requested_by, 'role', '').lower() == 'treasury'
    if is_treasury_request:
        tier = requisition.tier
        if tier in ["Tier 1", "Tier1"]:
            base_roles = ["department_head", "group_finance_manager"]
        elif tier in ["Tier 2", "Tier2", "Tier 3", "Tier3"]:
            base_roles = ["group_finance_manager", "cfo"]
        elif tier in ["Tier 4", "Tier4"]:
            base_roles = ["cfo", "ceo"]

    # Remove requester role if self-approval not allowed
    if not allow_self_approval:
        requester_role = getattr(requisition.requested_by, 'role', '').upper()
        base_roles = [r for r in base_roles if str(r).upper() != requester_role]

    # Apply payment thresholds (ensure cfo/ceo included when amount demands)
    try:
        max_without_cfo = float(get_setting('MAX_PAYMENT_AMOUNT_WITHOUT_CFO', '500000'))
        max_without_ceo = float(get_setting('MAX_PAYMENT_AMOUNT_WITHOUT_CEO', '1000000'))
    except Exception:
        max_without_cfo = 500000.0
        max_without_ceo = 1000000.0

    if requisition.amount > max_without_ceo:
        if 'ceo' not in [r.lower() for r in base_roles]:
            base_roles.append('ceo')
    elif requisition.amount > max_without_cfo:
        if 'cfo' not in [r.lower() for r in base_roles]:
            base_roles.append('cfo')

    return base_roles


def find_candidate_for_role(role, requisition):
    """Find a candidate user for a role, applying scoping rules.

    Returns a User instance or None.
    """
    normalized_role = str(role).lower()
    candidates = User.objects.filter(role__iexact=normalized_role, is_active=True).exclude(id=requisition.requested_by.id)

    # centralized roles are not scoped
    if normalized_role not in [r.lower() for r in CENTRALIZED_ROLES]:
        if getattr(requisition, 'origin_type', '').lower() == 'branch' and getattr(requisition, 'branch', None):
            candidates = candidates.filter(branch=requisition.branch)
        elif getattr(requisition, 'origin_type', '').lower() == 'hq' and getattr(requisition, 'company', None):
            candidates = candidates.filter(company=requisition.company)
        elif getattr(requisition, 'origin_type', '').lower() == 'field' and getattr(requisition, 'region', None):
            candidates = candidates.filter(region=requisition.region)

    return candidates.first()


def resolve_candidate_list(base_roles, requisition, parallel_approvals=False):
    """Resolve a list of candidate approvers from base roles.

    Returns resolved list of dicts: {user_id, role, auto_escalated, parallel_approved}
    """
    resolved = []
    for role in base_roles:
        if str(role).lower() == 'staff':
            continue

        candidate = find_candidate_for_role(role, requisition)
        if candidate:
            resolved.append({
                'user_id': candidate.id,
                'role': role,
                'auto_escalated': False,
                'parallel_approved': parallel_approvals,
            })
        else:
            resolved.append({
                'user_id': None,
                'role': role,
                'auto_escalated': True,
                'parallel_approved': parallel_approvals,
            })

    return resolved


def apply_auto_escalation(resolved):
    """Fill in user_id for None entries by escalating to next available approver or admin.

    Modifies and returns the resolved list.
    """
    for i, r in enumerate(resolved):
        if r['user_id'] is None:
            next_approver = None
            for j in range(i + 1, len(resolved)):
                if resolved[j]['user_id'] is not None:
                    next_approver = resolved[j]
                    break

            if next_approver:
                r['user_id'] = next_approver['user_id']
                r['auto_escalated'] = True
                r['escalation_reason'] = f"No {r['role']} found, escalated to {next_approver['role']}"
            else:
                admin = User.objects.filter(role__iexact='admin', is_active=True).first()
                if admin:
                    r['user_id'] = admin.id
                    r['role'] = 'ADMIN'
                    r['auto_escalated'] = True
                    r['escalation_reason'] = f"No {r['role']} found, escalated to ADMIN"

    return resolved


def assign_slas(requisition, track_metrics=True, business_hours_only=False, weekend_processing=False):
    """Assign SLA deadlines on the requisition if not present.

    This mirrors existing SLA assignment logic used by the resolver.
    """
    if not track_metrics:
        return

    try:
        end_to_end_sla = int(get_setting('END_TO_END_SLA_DAYS', '5'))
        payment_sla = int(get_setting('PAYMENT_SLA_HOURS', '24'))
    except Exception:
        end_to_end_sla = 5
        payment_sla = 24

    if not getattr(requisition, 'end_to_end_sla_deadline', None):
        requisition.end_to_end_sla_deadline = requisition.created_at + timezone.timedelta(days=end_to_end_sla)
        requisition.save(update_fields=['end_to_end_sla_deadline'])

    if not getattr(requisition, 'payment_sla_deadline', None):
        requisition.payment_sla_deadline = requisition.created_at + timezone.timedelta(hours=payment_sla)
        requisition.save(update_fields=['payment_sla_deadline'])

    return
