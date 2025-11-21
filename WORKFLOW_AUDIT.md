# Approval Workflow Audit & Improvement Plan

## Current Implementation Analysis

### Issues Identified

#### 1. **Duplicate Workflow Resolution Logic** ⚠️
- **Location**: `transactions/models.py` (Requisition.resolve_workflow) AND `workflow/services/resolver.py` (resolve_workflow)
- **Problem**: Two different implementations with different logic
- **Impact**: Inconsistency, maintenance nightmare, hard to test
- **Fix**: Consolidate to single source of truth

#### 2. **Inconsistent Role Handling** ⚠️
- Model method normalizes: `role.lower()`
- Resolver service has redundant: `role.lower().replace("_", "_")`  (does nothing)
- **Impact**: Confusing, potential bugs
- **Fix**: Standardize role normalization

#### 3. **Missing Validation** ❌
- No validation that amount > 0
- No validation that origin_type matches org structure (branch request must have branch)
- No validation that workflow_sequence is not empty before approval
- **Impact**: Invalid data can enter system
- **Fix**: Add model validation

#### 4. **Auto-Escalation Edge Cases** ⚠️
- Model: Escalates to admin if no candidate found (adds to resolved list)
- Resolver: Sets user_id=None then replaces with admin later
- **Problem**: Different approaches, confusing flow
- **Impact**: Hard to track what happened in audit trail
- **Fix**: Consistent escalation strategy

#### 5. **Urgent Fast-Track Logic Flaw** 🐛
- Model: `resolved = [resolved[-1]]` - jumps to last
- Resolver: Same logic
- **Problem**: If last approver doesn't exist (user_id=None), crashes
- **Impact**: Urgent requests fail
- **Fix**: Validate resolved list before fast-track

#### 6. **No Atomic Approval Transaction** ❌
- `approve_requisition` view creates approval trail, updates requisition, creates payment
- **Problem**: If payment creation fails, requisition still marked reviewed
- **Impact**: Data inconsistency
- **Fix**: Use database transaction

#### 7. **Rejection Flow Not Tested** ⚠️
- Rejection exists in view but no clear workflow
- What happens to workflow_sequence when rejected?
- Can it be re-submitted?
- **Impact**: Undefined behavior
- **Fix**: Define rejection lifecycle

#### 8. **Centralized Roles Not Applied in Model** 🐛
- Model method applies scope filtering to ALL roles
- Resolver service has centralized_roles exception
- **Problem**: Model will filter treasury/CFO by branch (wrong!)
- **Impact**: High-level approvers not found
- **Fix**: Apply centralized logic in model

#### 9. **Treasury Override Only in Resolver** ⚠️
- Model doesn't handle treasury-created requisitions specially
- Resolver has treasury override logic
- **Problem**: If model method is used, treasury can approve own requests
- **Impact**: Segregation of duties violation
- **Fix**: Move treasury logic to model or always use resolver

#### 10. **No Workflow State Validation** ❌
- Can approve a rejected requisition?
- Can approve a paid requisition?
- No state machine validation
- **Impact**: Invalid state transitions
- **Fix**: Add state validation

---

## Proposed Fixes

### Priority 1: Critical Security Issues

#### Fix 1: Consolidate Workflow Resolution
**Action**: Use ONLY `workflow/services/resolver.py`, remove duplicate from model

```python
# transactions/models.py
def resolve_workflow(self):
    """Delegate to centralized resolver service"""
    from workflow.services.resolver import resolve_workflow
    return resolve_workflow(self)
```

#### Fix 2: Add Model Validation
```python
class Requisition(models.Model):
    def clean(self):
        # Validate amount
        if self.amount <= 0:
            raise ValidationError("Amount must be greater than zero")
        
        # Validate org structure matches origin
        if self.origin_type == 'branch' and not self.branch:
            raise ValidationError("Branch requests must have a branch")
        if self.origin_type == 'hq' and not self.company:
            raise ValidationError("HQ requests must have a company")
        if self.origin_type == 'field' and not self.region:
            raise ValidationError("Field requests must have a region")
```

#### Fix 3: Add State Machine Validation
```python
def can_approve(self, user):
    # Check status
    if self.status != 'pending':
        return False  # Can only approve pending requisitions
    
    # Check user is next approver
    if not self.next_approver or user.id != self.next_approver.id:
        return False
    
    # No self-approval
    if user.id == self.requested_by.id:
        return False
    
    return True
```

#### Fix 4: Atomic Approval Transaction
```python
from django.db import transaction

@login_required
@transaction.atomic
def approve_requisition(request, requisition_id):
    requisition = get_object_or_404(Requisition, transaction_id=requisition_id)
    
    # Validation
    if not requisition.can_approve(request.user):
        return HttpResponseForbidden("You cannot approve this requisition.")
    
    # Lock the row
    requisition = Requisition.objects.select_for_update().get(
        transaction_id=requisition_id
    )
    
    # Create approval trail
    ApprovalTrail.objects.create(...)
    
    # Update workflow
    workflow_seq = requisition.workflow_sequence or []
    if len(workflow_seq) > 1:
        # More approvers
        ...
    else:
        # Final approval
        requisition.status = "reviewed"
        requisition.save()
        
        # Create payment (within same transaction)
        Payment.objects.get_or_create(...)
    
    # If anything fails, entire transaction rolls back
```

### Priority 2: Consistency & Maintainability

#### Fix 5: Standardize Centralized Roles
```python
CENTRALIZED_ROLES = ['treasury', 'fp&a', 'group_finance_manager', 'cfo', 'ceo', 'admin']

def should_apply_scope_filter(role):
    return role.lower() not in CENTRALIZED_ROLES
```

#### Fix 6: Improve Auto-Escalation Tracking
```python
# When escalating, preserve original role in audit
resolved.append({
    "user_id": admin.id,
    "role": "admin",
    "auto_escalated": True,
    "original_role": role,  # Track what we couldn't find
    "escalation_reason": "No candidate found"
})
```

#### Fix 7: Define Rejection Lifecycle
```python
@login_required
@transaction.atomic
def reject_requisition(request, requisition_id):
    requisition = get_object_or_404(Requisition, transaction_id=requisition_id)
    
    # Only pending requisitions can be rejected
    if requisition.status != 'pending':
        return HttpResponseForbidden("Can only reject pending requisitions")
    
    # Create rejection trail
    ApprovalTrail.objects.create(
        requisition=requisition,
        user=request.user,
        action='rejected',
        ...
    )
    
    # Clear workflow
    requisition.status = 'rejected'
    requisition.workflow_sequence = []
    requisition.next_approver = None
    requisition.save()
```

---

## Comprehensive Test Plan

### Unit Tests

#### Test Suite 1: Threshold Matching
```python
def test_find_threshold_tier1():
    """Amount 500 should match Tier 1 (0-1000)"""

def test_find_threshold_tier2():
    """Amount 5000 should match Tier 2 (1000.01-10000)"""

def test_find_threshold_edge_case_exact_boundary():
    """Amount 1000.00 should match Tier 1, 1000.01 should match Tier 2"""

def test_find_threshold_no_match():
    """Amount 100000 with no tier should return None"""

def test_find_threshold_origin_type_specific():
    """Branch origin should prefer branch-specific threshold over ANY"""
```

#### Test Suite 2: Role Resolution
```python
def test_resolve_workflow_single_approver():
    """Tier 1 with single branch manager"""

def test_resolve_workflow_multi_approver():
    """Tier 2 with branch manager -> finance"""

def test_resolve_workflow_case_insensitive():
    """BRANCH_MANAGER should match branch_manager in DB"""

def test_resolve_workflow_self_approval_excluded():
    """Branch manager creating request should escalate to admin"""

def test_resolve_workflow_centralized_role_no_scope():
    """Treasury should not be filtered by branch"""

def test_resolve_workflow_scoped_role_with_scope():
    """Branch manager should be filtered by branch"""
```

#### Test Suite 3: Urgent Fast-Track
```python
def test_urgent_fast_track_multi_approver():
    """Urgent Tier 2 should skip to finance (last approver)"""

def test_urgent_fast_track_single_approver():
    """Urgent Tier 1 should still need branch manager (only 1 approver)"""

def test_urgent_fast_track_disabled():
    """Tier 3 with allow_urgent_fasttrack=False should not fast-track"""
```

#### Test Suite 4: Auto-Escalation
```python
def test_auto_escalate_no_candidate():
    """If no branch manager exists, should escalate to admin"""

def test_auto_escalate_audit_trail():
    """Escalation should be tracked in approval trail"""

def test_auto_escalate_no_admin_fails():
    """If no admin exists, should raise ValueError"""
```

#### Test Suite 5: Approval Flow
```python
def test_approve_first_of_multi():
    """First approval should move to next approver"""

def test_approve_final():
    """Final approval should mark as reviewed and create payment"""

def test_approve_wrong_user():
    """Non-next-approver trying to approve should fail"""

def test_approve_self():
    """Requester trying to approve should fail"""

def test_approve_already_reviewed():
    """Approving reviewed requisition should fail"""

def test_approve_rejected():
    """Approving rejected requisition should fail"""
```

#### Test Suite 6: Rejection Flow
```python
def test_reject_pending():
    """Rejecting pending should set status to rejected"""

def test_reject_clears_workflow():
    """Rejection should clear next_approver and workflow_sequence"""

def test_reject_creates_trail():
    """Rejection should create approval trail with action=rejected"""

def test_reject_reviewed():
    """Cannot reject already reviewed requisition"""
```

#### Test Suite 7: Treasury Override
```python
def test_treasury_request_tier1():
    """Treasury Tier 1 should need dept head + group finance"""

def test_treasury_request_tier2():
    """Treasury Tier 2 should need group finance + CFO"""

def test_treasury_no_self_approval():
    """Treasury cannot be in their own workflow"""
```

#### Test Suite 8: Edge Cases
```python
def test_empty_workflow_sequence():
    """Requisition with empty workflow should fail approval"""

def test_concurrent_approval_same_requisition():
    """Two approvers trying simultaneously should handle with locking"""

def test_workflow_with_deleted_user():
    """If next_approver is deleted, should handle gracefully"""

def test_amount_zero():
    """Amount = 0 should fail validation"""

def test_negative_amount():
    """Negative amount should fail validation"""

def test_origin_type_mismatch():
    """Branch origin with no branch should fail validation"""
```

### Integration Tests

```python
def test_e2e_tier1_approval_to_payment():
    """Complete flow: create -> approve -> payment"""
    # Create staff user
    # Create branch manager
    # Create requisition (500)
    # Branch manager approves
    # Verify status = reviewed
    # Verify payment created
    # Treasury executes payment
    # Verify status = paid

def test_e2e_tier2_two_approvers():
    """Multi-approver flow"""
    # Create requisition (5000)
    # Branch manager approves
    # Verify status still pending
    # Finance approves
    # Verify status = reviewed

def test_e2e_urgent_fast_track():
    """Urgent request skips intermediate approvers"""
    # Create urgent requisition (5000)
    # Verify workflow has only finance (skipped branch)
    # Finance approves
    # Verify reviewed

def test_e2e_rejection_flow():
    """Rejection workflow"""
    # Create requisition
    # Branch manager rejects
    # Verify status = rejected
    # Verify cannot approve after rejection
```

---

## Implementation Checklist

### Phase 1: Fix Critical Issues (1-2 days)
- [ ] Consolidate workflow resolution to single service
- [ ] Add model validation (amount, org structure)
- [ ] Add state machine validation (status transitions)
- [ ] Add atomic transactions to approval/rejection
- [ ] Fix centralized roles filtering in model

### Phase 2: Write Test Suite (2-3 days)
- [ ] Create `tests/unit/test_approval_threshold.py`
- [ ] Create `tests/unit/test_workflow_resolver.py`
- [ ] Create `tests/unit/test_requisition_approval.py`
- [ ] Create `tests/integration/test_approval_e2e.py`
- [ ] Achieve >90% code coverage on workflow code

### Phase 3: Handle Edge Cases (1 day)
- [ ] Add concurrency handling (row locking)
- [ ] Add deleted user handling
- [ ] Add validation error messages
- [ ] Add logging for audit trail

### Phase 4: Documentation (1 day)
- [ ] Document state machine diagram
- [ ] Document all validation rules
- [ ] Document escalation rules
- [ ] Update API documentation

---

## Success Criteria

✅ All tests passing (>90% coverage)
✅ No duplicate logic between model and resolver
✅ All state transitions validated
✅ Atomic approval/rejection operations
✅ Comprehensive audit trail
✅ Edge cases handled gracefully
✅ Documentation complete

## Timeline

**Total: 5-7 days**
- Days 1-2: Fix critical issues
- Days 3-5: Write comprehensive tests
- Day 6: Edge cases & refinement
- Day 7: Documentation & review
