# Phase 5 — Treasury Payment Execution

## Overview

Phase 5 implements the **payment execution layer** for the petty cash system. After a requisition is approved through Phase 4 workflow, Phase 5 handles:

- Payment execution (MPESA, bank transfer, cash)
- Atomic transactions with rollback
- Treasury fund validation and balance tracking
- 2FA verification for treasury users
- Executor ≠ Requester segregation of duties
- Reconciliation and variance tracking
- Audit trail for all payments

---

## Core Principle: Segregation of Duties

**No user may execute their own payment.** This extends Phase 4's no-self-approval invariant to the execution layer.

- Requisition requester → cannot be payment executor
- Treasury self-requests → executed by different treasury officer
- All payment executions logged with executor_id ≠ requested_by_id

---

## Phase 5 Data Models

### 1. TreasuryFund (Company/Region/Branch-level)

```python
TreasuryFund:
  fund_id (UUID, PK)
  company (FK)
  region (FK, nullable)
  branch (FK, nullable)
  current_balance (Decimal)
  last_replenished (DateTime)
  reorder_level (Decimal)  # Alert when balance < this
  ledger_entries (Reverse FK to LedgerEntry)
  created_at, updated_at
```

**Behavior:**
- Track cash balance per location
- Auto-trigger ReplenishmentRequest when balance < reorder_level
- Only Treasury can modify balance
- Immutable audit trail of all changes

### 2. Payment (Pending Payment Record)

```python
Payment:
  payment_id (UUID, PK)
  requisition (FK)
  amount (Decimal)
  method (Choice: 'MPESA', 'BANK', 'CASH')
  destination (CharField, e.g., phone number or account)
  status (Choice: 'pending', 'executing', 'success', 'failed', 'reconciled')
  
  # Executor segregation
  executor (FK, initially None)
  execution_timestamp (DateTime, null)
  
  # 2FA
  otp_required (Boolean)
  otp_sent_timestamp (DateTime, nullable)
  otp_verified (Boolean)
  
  # Retry tracking
  retry_count (Integer, default=0)
  max_retries (Integer, default=3)
  last_error (TextField, nullable)
  
  created_at, updated_at
```

### 3. PaymentExecution (After successful payment)

```python
PaymentExecution:
  execution_id (UUID, PK)
  payment (FK)
  executor (FK, NOT NULL)  # Who executed it
  execution_timestamp (DateTime)
  
  # Gateway response
  gateway_reference (CharField, unique)
  gateway_status (CharField)
  
  # 2FA
  otp_verified_at (DateTime)
  otp_verified_by (FK to User)
  
  # Audit
  ip_address (GenericIPAddress)
  user_agent (TextField)
  
  created_at
```

### 4. LedgerEntry (Fund transaction record)

```python
LedgerEntry:
  entry_id (UUID, PK)
  treasury_fund (FK)
  payment_execution (FK, nullable)
  entry_type (Choice: 'debit', 'credit', 'adjustment')
  amount (Decimal)
  
  # Reconciliation
  reconciled (Boolean, default=False)
  reconciled_by (FK, nullable)
  reconciliation_timestamp (DateTime, nullable)
  
  description (TextField)
  created_at
```

### 5. VarianceAdjustment (For reconciliation mismatches)

```python
VarianceAdjustment:
  adjustment_id (UUID, PK)
  treasury_fund (FK)
  original_amount (Decimal)
  adjusted_amount (Decimal)
  variance_amount (Decimal)  # adjusted - original
  reason (TextField)
  
  initiated_by (FK)
  approved_by (FK, CFO only)
  status (Choice: 'pending', 'approved', 'rejected')
  
  created_at, approved_at
```

### 6. ReplenishmentRequest (Auto-trigger when low on funds)

```python
ReplenishmentRequest:
  request_id (UUID, PK)
  treasury_fund (FK)
  current_balance (Decimal)
  requested_amount (Decimal)
  reason (TextField)
  
  status (Choice: 'pending', 'approved', 'funded', 'rejected')
  approved_by (FK)
  
  created_at, approved_at
```

---

## Phase 5 Workflow

### Payment Execution Flow (Happy Path)

```
1. Requisition Approved (Phase 4)
   ↓
2. Create Payment record (status: pending)
   - Validate executor ≠ requester
   - Set executor (from workflow last approver or Treasury pool)
   ↓
3. Treasury User Initiates Payment
   - Load payment form with amount, method, destination
   - Verify executor_id ≠ requisition.requested_by_id
   - Trigger 2FA (OTP to registered phone)
   ↓
4. 2FA Verification
   - User enters OTP
   - Verify against sent OTP
   - Mark otp_verified=True
   ↓
5. Atomic Payment Transaction
   with transaction.atomic():
     a. Validate TreasuryFund.current_balance ≥ amount
     b. Call payment gateway (MPESA/Bank API)
     c. If success:
        - Create PaymentExecution record
        - Debit TreasuryFund (current_balance -= amount)
        - Create LedgerEntry (debit)
        - Update Payment.status = 'success'
        - Update Requisition.status = 'paid'
     d. If failure:
        - Update Payment.status = 'failed'
        - Increment Payment.retry_count
        - Queue retry if retry_count < max_retries
        - Create ApprovalTrail with error
   ↓
6. Post-Payment
   - Send confirmation SMS/email to requester
   - Mark for FP&A review
   - Check if TreasuryFund.current_balance < reorder_level
   - If yes: Auto-trigger ReplenishmentRequest
```

### Error Handling & Retry

```
On Payment Failure:
1. Retry immediately (up to 3 times)
2. Each retry logs attempt in PaymentExecution
3. If all retries fail:
   - Mark as 'failed'
   - Alert Treasury/CFO
   - Create incident record
   - Maintain Payment for manual retry
```

### Reconciliation Flow

```
Daily/Weekly Reconciliation:
1. FP&A pulls LedgerEntry records (reconciled=False)
2. Cross-check with bank/MPESA statement
3. For each entry:
   - If matched: Mark reconciled=True, reconciled_by=fpanda_user, timestamp
   - If mismatch: Create VarianceAdjustment (pending approval)
4. CFO reviews VarianceAdjustments
5. If approved: Apply adjustment to TreasuryFund balance
6. Generate reconciliation report
```

---

## Phase 5 API Endpoints

### POST /payments/{payment_id}/execute/
- Input: OTP (if required), method, destination
- Check: executor ≠ requester
- Check: 2FA (if required)
- Check: Balance ≥ amount
- Return: PaymentExecution record or error
- Status: 403 if executor == requester
- Status: 400 if OTP invalid
- Status: 402 if insufficient funds

### POST /payments/{payment_id}/verify-otp/
- Input: OTP
- Validate OTP against sent value & timestamp (5 min expiry)
- Return: {verified: true/false}

### POST /treasury-funds/{fund_id}/replenish/
- Admin only
- Input: amount
- Creates credit LedgerEntry
- Updates TreasuryFund.current_balance

### GET /payments/{payment_id}/
- Return: Payment record with execution status

### GET /treasury-funds/{fund_id}/balance/
- Return: current_balance, reorder_level, last_replenished

### POST /reconciliation/
- FP&A only
- Input: reconciliation data (date range, entries to match)
- Return: reconciliation report with variances

---

## Key Enforcement Rules

### Executor Segregation of Duties
```python
def can_execute(executor_user, payment):
    # Cannot execute own requisition payment
    if executor_user.id == payment.requisition.requested_by_id:
        return False
    
    # Must be Treasury or authorized approver
    if executor_user.role.lower() not in ['treasury', 'cfo', 'admin']:
        return False
    
    # If Treasury self-request: must be different treasury officer
    if payment.requisition.requested_by.role.lower() == 'treasury':
        if executor_user.role.lower() == 'treasury':
            # Find a different treasury officer
            other_treasury = User.objects.filter(
                role='treasury',
                is_active=True
            ).exclude(id=executor_user.id).first()
            if not other_treasury:
                return False
    
    return True
```

### 2FA Implementation
```python
def send_otp(payment, executor_user):
    otp = generate_otp(6 digits)
    send_sms(executor_user.phone_number, f"OTP: {otp}")
    payment.otp_sent_timestamp = timezone.now()
    payment.save()
    # OTP valid for 5 minutes
    
def verify_otp(payment, provided_otp):
    if not payment.otp_sent_timestamp:
        return False
    
    elapsed = timezone.now() - payment.otp_sent_timestamp
    if elapsed.total_seconds() > 300:  # 5 minutes
        return False
    
    if provided_otp != payment.otp:  # Hashed in production
        return False
    
    payment.otp_verified = True
    payment.save()
    return True
```

### Atomic Payment Processing
```python
def execute_payment_atomic(payment, executor_user, otp):
    # Pre-checks
    if not can_execute(executor_user, payment):
        raise PermissionDenied("Executor cannot execute this payment")
    
    if not verify_otp(payment, otp):
        raise ValidationError("Invalid or expired OTP")
    
    # Atomic transaction
    with transaction.atomic():
        # Lock for update (prevent race conditions)
        fund = TreasuryFund.objects.select_for_update().get(...)
        
        if fund.current_balance < payment.amount:
            raise InsufficientFundsError()
        
        # Call payment gateway
        try:
            result = payment_gateway.disburse(
                amount=payment.amount,
                method=payment.method,
                destination=payment.destination
            )
        except PaymentGatewayError as e:
            payment.status = 'failed'
            payment.last_error = str(e)
            payment.retry_count += 1
            payment.save()
            if payment.retry_count < payment.max_retries:
                queue_payment_retry(payment)
            raise
        
        # Success: create execution record
        execution = PaymentExecution.objects.create(
            payment=payment,
            executor=executor_user,
            execution_timestamp=timezone.now(),
            gateway_reference=result.reference,
            gateway_status=result.status,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        # Debit fund
        fund.current_balance -= payment.amount
        fund.save()
        
        # Create ledger entry
        LedgerEntry.objects.create(
            treasury_fund=fund,
            payment_execution=execution,
            entry_type='debit',
            amount=payment.amount,
            description=f"Payment for requisition {payment.requisition.transaction_id}"
        )
        
        # Update payment status
        payment.status = 'success'
        payment.executor = executor_user
        payment.execution_timestamp = timezone.now()
        payment.save()
        
        # Update requisition
        payment.requisition.status = 'paid'
        payment.requisition.save()
        
        # Check replenishment threshold
        if fund.current_balance < fund.reorder_level:
            ReplenishmentRequest.objects.create(
                treasury_fund=fund,
                current_balance=fund.current_balance,
                requested_amount=fund.reorder_level * 2,  # Request to double reorder level
                reason=f"Auto-triggered. Balance {fund.current_balance} < Reorder Level {fund.reorder_level}"
            )
        
        # Audit trail
        ApprovalTrail.objects.create(
            requisition=payment.requisition,
            user=executor_user,
            role=executor_user.role,
            action='paid',
            comment=f"Payment executed: {payment.method} to {payment.destination}",
            timestamp=timezone.now(),
            ip_address=get_client_ip(request)
        )
        
        return execution
```

---

## Phase 5 Testing Strategy

### Unit Tests
1. `test_can_execute_self_payment_denied` — Executor cannot execute own payment
2. `test_can_execute_treasury_different_officer` — Treasury payment needs different officer
3. `test_otp_generation_and_validation` — OTP lifecycle
4. `test_otp_expiry_after_5_minutes` — OTP timeout
5. `test_atomic_payment_success` — Full atomic transaction
6. `test_atomic_payment_rollback_on_gateway_error` — Rollback on failure
7. `test_insufficient_funds_error` — Balance check
8. `test_retry_mechanism` — Retry on failure
9. `test_ledger_entry_created` — Ledger tracking
10. `test_reorder_level_trigger` — Auto-replenishment

### Integration Tests
1. `test_end_to_end_payment_flow` — From requisition approval to payment success
2. `test_payment_reconciliation` — FP&A reconciliation workflow
3. `test_variance_adjustment_approval` — CFO approval of variances

### API Tests
1. `test_execute_payment_endpoint_403_for_requester` — API enforces segregation
2. `test_execute_payment_endpoint_400_invalid_otp` — OTP validation
3. `test_execute_payment_endpoint_402_insufficient_funds` — Balance check

---

## Rollout Checklist

- [ ] All Phase 5 models created & migrated
- [ ] Payment execution logic implemented (atomic, retry)
- [ ] 2FA service integrated (SMS/Email)
- [ ] Payment gateway integration (MPESA mock or real)
- [ ] Executor segregation enforced at API & model layer
- [ ] All 10+ unit tests passing
- [ ] Integration tests passing
- [ ] API tests passing
- [ ] Reconciliation workflow tested
- [ ] Variance adjustment workflow tested
- [ ] Documentation updated
- [ ] Code review sign-off
- [ ] Staging environment tested
- [ ] Treasury & FP&A training completed
- [ ] Production rollout

---

## Success Metrics (Phase 5)

- ✅ Zero instances of self-payment execution
- ✅ 100% payment reconciliation rate
- ✅ <1% payment failure rate (with successful retry)
- ✅ <5 minute OTP validation time
- ✅ Zero race conditions on concurrent payments (via locking)
- ✅ All transactions atomic (all-or-nothing)
- ✅ Complete audit trail for all payments

---

## Next: Phase 6 (FP&A Oversight)

After Phase 5 is complete, Phase 6 will add:
- Post-payment FP&A review
- Analytics dashboards
- KPI tracking (approval SLA, payment SLA, variance %)
- Variance trend analysis
- Alerts for anomalies

