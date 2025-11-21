# Approval Workflow - Robust Testing & Improvement Plan

## ✅ Completed

### 1. Comprehensive Audit
**File:** `WORKFLOW_AUDIT.md`

**10 Critical Issues Identified:**
1. Duplicate workflow resolution logic (model + service)
2. Inconsistent role handling
3. Missing validation (amount, org structure)
4. Auto-escalation edge cases
5. Urgent fast-track logic flaws
6. No atomic approval transactions
7. Rejection flow not tested
8. Centralized roles not applied in model
9. Treasury override only in resolver
10. No workflow state validation

### 2. Test Suite Created
**Location:** `tests/`

#### Unit Tests:
- **`tests/unit/test_approval_threshold.py`** (14 tests)
  - Tier matching (boundaries, middle values)
  - Origin-specific priorities
  - Inactive threshold filtering
  - Case-insensitive origin matching
  - Decimal precision at boundaries

- **`tests/unit/test_workflow_resolver.py`** (15 tests)
  - Single/multi-approver assignment
  - Case-insensitive role matching
  - Self-approval prevention
  - Centralized vs scoped role filtering
  - Auto-escalation
  - Urgent fast-track (enabled/disabled)
  - Treasury override rules
  - Workflow order preservation

- **`tests/unit/test_requisition_approval.py`** (15 tests)
  - Can approve validation
  - Approval flow (first, intermediate, final)
  - State transitions (pending → reviewed)
  - Payment creation on final approval
  - Rejection flow
  - Edge cases (zero/negative amounts, missing data)

#### Integration Tests:
- **`tests/integration/test_approval_e2e.py`** (5 test suites)
  - Complete Tier 1 flow (create → approve → payment)
  - Complete Tier 2 flow (multi-approver)
  - Urgent request fast-track
  - Rejection workflow
  - End-to-end scenarios with real audit trails

**Total: 49 comprehensive tests**

## 📋 Next Steps

### Phase 1: Run Tests & Identify Failures
```bash
# Run all tests
python manage.py test tests/unit tests/integration

# Run with coverage
coverage run --source='.' manage.py test tests/
coverage report
coverage html
```

**Expected:** Many tests will fail because:
- Model validation not implemented
- Atomic transactions not implemented
- Edge cases not handled
- Duplicate logic conflicts

### Phase 2: Fix Critical Issues (Priority Order)

#### 1. Consolidate Workflow Resolution (HIGH)
**Current:** Two implementations
```python
# transactions/models.py - DELETE this
def resolve_workflow(self):
    # Duplicate logic...

# Keep ONLY workflow/services/resolver.py
```

**Fix:** Make model delegate to service
```python
# transactions/models.py
def resolve_workflow(self):
    from workflow.services.resolver import resolve_workflow
    return resolve_workflow(self)
```

#### 2. Add Model Validation (HIGH)
```python
# transactions/models.py
from django.core.exceptions import ValidationError

class Requisition(models.Model):
    def clean(self):
        # Validate amount
        if self.amount and self.amount <= 0:
            raise ValidationError({'amount': 'Amount must be greater than zero'})
        
        # Validate org structure matches origin
        if self.origin_type == 'branch' and not self.branch:
            raise ValidationError({'branch': 'Branch requests must have a branch'})
        if self.origin_type == 'hq' and not self.company:
            raise ValidationError({'company': 'HQ requests must have a company'})
        if self.origin_type == 'field' and not self.region:
            raise ValidationError({'region': 'Field requests must have a region'})
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
```

#### 3. Add State Machine Validation (HIGH)
```python
# transactions/models.py
def can_approve(self, user):
    # Check status - only pending can be approved
    if self.status != 'pending':
        return False
    
    # No self-approval
    if user.id == self.requested_by.id:
        return False
    
    # Must be next approver
    if not self.next_approver or user.id != self.next_approver.id:
        return False
    
    return True
```

#### 4. Add Atomic Transactions (HIGH)
```python
# transactions/views.py
from django.db import transaction

@login_required
@transaction.atomic
def approve_requisition(request, requisition_id):
    # Lock row for update
    requisition = Requisition.objects.select_for_update().get(
        transaction_id=requisition_id
    )
    
    if not requisition.can_approve(request.user):
        return HttpResponseForbidden("You cannot approve this requisition.")
    
    # Create approval trail
    ApprovalTrail.objects.create(...)
    
    # Update workflow
    # ...
    
    # If final approval, create payment (same transaction)
    if not workflow_seq:
        Payment.objects.get_or_create(...)
    
    # All or nothing - transaction rolls back on any error
```

#### 5. Fix Centralized Roles in Model (MEDIUM)
```python
# transactions/models.py
CENTRALIZED_ROLES = ['treasury', 'fp&a', 'group_finance_manager', 'cfo', 'ceo', 'admin']

def resolve_workflow(self):
    # ...
    for role in roles_sequence:
        normalized_role = role.lower()
        candidates = User.objects.filter(role=normalized_role, is_active=True)
        
        # Apply scope filtering ONLY for non-centralized roles
        if normalized_role not in CENTRALIZED_ROLES:
            if self.origin_type == 'branch' and self.branch:
                candidates = candidates.filter(branch=self.branch)
            # ...
```

#### 6. Improve Rejection Flow (MEDIUM)
```python
@login_required
@transaction.atomic
def reject_requisition(request, requisition_id):
    requisition = Requisition.objects.select_for_update().get(
        transaction_id=requisition_id
    )
    
    # Validate can reject
    if requisition.status != 'pending':
        messages.error(request, "Can only reject pending requisitions")
        return redirect('transactions-home')
    
    if not requisition.can_approve(request.user):
        return HttpResponseForbidden("You cannot reject this requisition.")
    
    # Create rejection trail
    ApprovalTrail.objects.create(
        requisition=requisition,
        user=request.user,
        role=request.user.role,
        action='rejected',
        comment=request.POST.get("comment", ""),
        timestamp=timezone.now()
    )
    
    # Clear workflow
    requisition.status = 'rejected'
    requisition.workflow_sequence = []
    requisition.next_approver = None
    requisition.save()
    
    messages.success(request, f"Requisition {requisition_id} rejected.")
    return redirect("transactions-home")
```

### Phase 3: Run Tests Again
After each fix, run tests to verify:
```bash
python manage.py test tests/unit/test_approval_threshold.py
python manage.py test tests/unit/test_workflow_resolver.py
python manage.py test tests/unit/test_requisition_approval.py
python manage.py test tests/integration/test_approval_e2e.py
```

### Phase 4: Deploy to Render
Once all tests pass:
```bash
git add .
git commit -m "Robust approval workflow with comprehensive tests"
git push origin main
```

## 📊 Test Coverage Goals

| Component | Current | Target |
|-----------|---------|--------|
| `workflow/services/resolver.py` | 0% | >90% |
| `transactions/models.py` (Requisition) | ~40% | >90% |
| `transactions/views.py` (approval) | ~30% | >90% |
| `workflow/models.py` (ApprovalThreshold) | 0% | >80% |

## 🎯 Success Criteria

Before deploying to production:
- [ ] All 49 tests passing
- [ ] Code coverage >90% on workflow logic
- [ ] No duplicate workflow resolution logic
- [ ] All state transitions validated
- [ ] Atomic approval/rejection operations
- [ ] Model validation enforced
- [ ] Edge cases handled gracefully
- [ ] Documentation updated

## 🚀 Timeline

**Phase 1-2: Fix Critical Issues** (1-2 days)
- Consolidate workflow resolution
- Add model validation
- Add state machine validation
- Add atomic transactions
- Run tests and iterate

**Phase 3: Fix Remaining Issues** (1 day)
- Handle edge cases
- Improve error messages
- Add logging
- Polish UX

**Phase 4: Documentation & Deploy** (0.5 days)
- Update APPROVAL_WORKFLOW_EXAMPLE.md
- Create TESTING.md guide
- Deploy to Render
- Run smoke tests

**Total: 2.5-3.5 days**

## 📝 Files Created

1. `WORKFLOW_AUDIT.md` - Complete audit with 10 issues identified
2. `tests/unit/test_approval_threshold.py` - 14 tests
3. `tests/unit/test_workflow_resolver.py` - 15 tests
4. `tests/unit/test_requisition_approval.py` - 15 tests
5. `tests/integration/test_approval_e2e.py` - 5 test suites
6. `WORKFLOW_TESTING_SUMMARY.md` - This file

## 🔧 How to Run Tests

```bash
# Navigate to project
cd C:\Users\ADMIN\pettycash_system

# Activate virtual environment
venv\Scripts\activate

# Run all approval workflow tests
python manage.py test tests.unit tests.integration

# Run specific test file
python manage.py test tests.unit.test_approval_threshold

# Run specific test case
python manage.py test tests.unit.test_workflow_resolver.WorkflowResolutionTests.test_resolve_workflow_tier1_single_approver

# Run with verbose output
python manage.py test tests.unit -v 2

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test tests/
coverage report
coverage html  # Creates htmlcov/index.html
```

## 🐛 Known Issues to Fix

From audit, these MUST be fixed before production:

1. **Duplicate logic** - Model and service both implement workflow resolution
2. **No validation** - Can create requisition with amount=0, negative, or mismatched org structure
3. **Race conditions** - Multiple approvers can approve simultaneously
4. **Incomplete rejection** - No clear lifecycle for rejected requisitions
5. **Treasury override missing** - Model doesn't prevent treasury self-approval
6. **Centralized roles** - Model filters treasury/CFO by branch (wrong!)

## 💡 Recommended: Start Here

1. **Run tests** to see current state:
   ```bash
   python manage.py test tests.unit.test_approval_threshold -v 2
   ```

2. **Fix #1 issue first** (duplicate logic):
   - Update `transactions/models.py` to delegate to service
   - Remove duplicate resolution code

3. **Run tests again** - should pass more tests

4. **Fix #2 issue** (validation):
   - Add `clean()` method to Requisition model
   - Call `full_clean()` before save

5. **Continue iterating** through issues in priority order

---

**Ready to make the approval workflow production-ready with comprehensive test coverage!**
