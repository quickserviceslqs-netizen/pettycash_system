# Phase 4 — No-Self-Approval Invariant Verification Checklist

## Overview
Phase 4 implements the core security invariant: **No user may approve or execute their own requisition.**

This invariant is enforced across **four layers**: routing, model, API, and UI.

---

## ✅ Phase 4 Verification Points

### 1. **Model Layer Enforcement**
- [ ] `Requisition.can_approve(user)` returns `False` when `user.id == requisition.requested_by_id`
- [ ] `Requisition.can_approve(user)` returns `False` when `user.id != requisition.next_approver_id`
- [ ] `Requisition.can_approve(user)` returns `True` only when both conditions pass
- [ ] `ApprovalTrail` records `auto_escalated=True` when requester would have approved
- [ ] `ApprovalTrail` captures `skipped_roles` for escalations
- [ ] Model validation prevents self-approval attempt at save time (if applicable)

### 2. **Routing Engine (Workflow Resolution)**
- [ ] `resolve_workflow()` excludes `requested_by` user from all role candidates
- [ ] If no candidate found for a role, `auto_escalated=True` is set in resolved sequence
- [ ] Treasury-originated requests (requester.role == 'TREASURY') trigger alternate approval sequences
  - [ ] Tier 1 → ["DEPT_HEAD", "GROUP_FINANCE_MANAGER"]
  - [ ] Tier 2/3 → ["GROUP_FINANCE_MANAGER", "CFO"]
  - [ ] Tier 4 → ["CFO", "CEO"]
- [ ] Treasury is excluded from approving/executing their own request
- [ ] If Treasury and no alternate executor found, escalate to CFO with auto-escalation flag
- [ ] Centralized roles (CFO, Treasury, FP&A) are not scoped by branch/region
- [ ] Scoped roles (Branch Manager, Dept Head) respect branch/region/company boundaries

### 3. **API/View Layer Enforcement**
- [ ] `approve_requisition()` view calls `can_approve()` before approving
- [ ] If `can_approve()` returns `False`, return HTTP 403 Forbidden
- [ ] `reject_requisition()` view calls `can_approve()` before rejecting
- [ ] If `can_approve()` returns `False`, return HTTP 403 Forbidden
- [ ] API logs all approval/rejection attempts (success and failures) with timestamp & IP
- [ ] API prevents direct URL manipulation (e.g., `GET /approve/<id>` requires POST)
- [ ] Error messages do not expose internal logic (generic "You cannot approve this requisition")

### 4. **UI Layer Behavior**
- [ ] Approve/Reject buttons are **hidden** or **disabled** when viewer is the requester
- [ ] Dashboard only shows "Pending Approvals" section if viewer is an approver role
- [ ] Requisition detail page displays banner if viewer is requester:
  - Message: "You cannot approve your own requisition — it will be routed to [Next Approver]."
- [ ] Approve/Reject buttons are **disabled** with tooltip on requester's own requisition
- [ ] If next_approver is null, banner shows "...routed to the next approver in the queue."

### 5. **Workflow Sequence Integrity**
- [ ] `workflow_sequence` JSON stores resolved approvers with correct user IDs and roles
- [ ] `next_approver_id` points to first user in `workflow_sequence`
- [ ] On each approval, the workflow advances: `workflow_sequence.pop(0)`, next_approver updates
- [ ] If workflow exhausted (all approvals done), status → "reviewed" or "paid"
- [ ] No approver can skip steps or self-approve mid-workflow

### 6. **Rejection Handling**
- [ ] Rejecting sets requisition status to "rejected"
- [ ] Only the current `next_approver` can reject
- [ ] Rejection creates `ApprovalTrail` with `action="rejected"` and reason
- [ ] Rejected requisition is visible to requester but not to other approvers
- [ ] Requester can re-submit a rejected requisition as a new draft

### 7. **Treasury Special Case (Phase 5 integration)**
- [ ] When `requisition.requested_by.role == 'TREASURY'`
  - [ ] `special_case` field is set to "Treasury Request"
  - [ ] Base approval sequence is replaced with alternate (see checkpoint 2)
- [ ] Treasury user cannot see approve/reject/execute controls on their own request
- [ ] Payment execution enforces `executor_id != requested_by_id`
- [ ] If no alternate treasury executor available, CFO assigns one manually
- [ ] Audit trail records "Treasury self-request detected" for all escalations

### 8. **Urgency & Fast-Track Override**
- [ ] `is_urgent=True` requires `urgency_reason` field to be populated
- [ ] First approver must confirm urgency; status becomes "pending_urgency_confirmation"
- [ ] If fast-track allowed (`allow_urgent_fasttrack=True`), workflow short-circuits to final approver
- [ ] Tier 4 requests cannot be fast-tracked
- [ ] Even in fast-track, no-self-approval invariant still applies
- [ ] If final approver == requester, escalation occurs anyway

### 9. **Audit Trail Completeness**
- [ ] Each approval/rejection/escalation creates `ApprovalTrail` entry
- [ ] `ApprovalTrail` includes:
  - `requisition` (FK)
  - `user` (who acted)
  - `role` (approver's role at time of action)
  - `action` (approved/rejected)
  - `comment` (reason/evidence)
  - `timestamp` (auto-captured)
  - `ip_address` (captured from request)
  - `auto_escalated` (True if escalation occurred)
  - `skipped_roles` (JSON of roles skipped due to no-candidate)
  - `override` (False by default; True only if admin overrides)
- [ ] Audit trail is **immutable** (no edits allowed after creation)
- [ ] 7+ years retention policy (document in app docs)

### 10. **Escalation Tracking**
- [ ] When no candidate found for a role, `auto_escalated=True` in workflow_sequence
- [ ] Escalation reason is recorded in `ApprovalTrail.skipped_roles` JSON
- [ ] If escalated to Admin, `ApprovalTrail.role="ADMIN"` and `auto_escalated=True`
- [ ] CFO/Audit can export escalation summary (count, reasons, affected requisitions)
- [ ] Escalations are highlighted/flagged in admin UI for review

### 11. **Error Handling & Edge Cases**
- [ ] No Admin/superuser exists → ValueError raised with clear message
- [ ] Requester is the only user in a role → Auto-escalate to next level
- [ ] Requisition has no next_approver → Status = "reviewed", no further action needed
- [ ] User manually edits `next_approver` field in DB → API still enforces can_approve()
- [ ] Concurrent approval attempts → Last write wins (or locking prevents race condition)
- [ ] Deleted user still in workflow → Escalate automatically to Admin
- [ ] Deactivated user (is_active=False) → Treat as no candidate, escalate

---

## Testing Strategy

### Unit Tests
1. **`test_can_approve_self_rejection`** — Requester cannot approve their own requisition
2. **`test_can_approve_wrong_approver`** — Non-next-approver cannot approve
3. **`test_can_approve_valid_approver`** — Next-approver can approve
4. **`test_resolve_workflow_excludes_requester`** — Workflow resolution skips requester
5. **`test_resolve_workflow_escalation`** — When no candidate, escalate to Admin
6. **`test_treasury_request_alternate_sequence`** — Treasury request routes to Finance/CFO
7. **`test_approval_trail_auto_escalated`** — ApprovalTrail records escalation
8. **`test_workflow_advance`** — Next approver advances after approval

### Integration Tests
1. **`test_full_approval_flow_no_self_approve`** — End-to-end requisition through approval chain
2. **`test_treasury_requisition_routing`** — Treasury submission routes to alternate approvers
3. **`test_urgent_fasttrack_no_self_approve`** — Urgent requisition fast-tracks but respects invariant
4. **`test_rejection_workflow`** — Requester cannot reject their own requisition
5. **`test_concurrent_approvals`** — Multiple approvals handled correctly

### API/View Tests
1. **`test_view_approve_forbidden_self`** — POST /approve/ returns 403 for requester
2. **`test_view_reject_forbidden_self`** — POST /reject/ returns 403 for requester
3. **`test_dashboard_no_self_in_pending`** — Requester's requisition not in requester's approval queue
4. **`test_ui_buttons_hidden_for_requester`** — Template hides approve/reject for requester

### Security Tests
1. **`test_direct_db_update_still_blocked`** — Even if next_approver manually changed, API rejects self-approval
2. **`test_sql_injection_prevention`** — Parameterized queries used throughout
3. **`test_csrf_protection`** — Approve/reject forms require CSRF token

---

## Rollout Checklist

- [ ] All 11 verification points confirmed
- [ ] All unit + integration + API tests passing (>95% code coverage)
- [ ] Security tests passing
- [ ] No self-approval violations found in test suite
- [ ] Audit trail correctly records escalations
- [ ] Treasury special case validated
- [ ] UI banners and disabled buttons working
- [ ] Error messages non-revealing
- [ ] Documentation updated with Phase 4 design
- [ ] Code review sign-off by 2+ reviewers
- [ ] Staging environment tested with real user workflows
- [ ] CFO/Admin training completed
- [ ] Monitoring & alerting set up for escalation anomalies
- [ ] Ready for Phase 5 Treasury Payment Execution

---

## Sign-Off

- **Phase Lead**: ___________________  
- **Date**: ___________________  
- **Notes**: ___________________

