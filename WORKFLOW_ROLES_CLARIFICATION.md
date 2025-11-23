# Workflow Roles Clarification

## Date: November 21, 2025

## Critical Distinction: Approvers vs. Validators vs. Reviewers

### 🔑 Key Principle
**Treasury does NOT approve requisitions - they validate and execute payment AFTER all approvals are complete.**

---

## Role Definitions

### 1. **Approvers** (Decision Makers)
These roles make approval decisions based on business justification:

- **Branch Manager** - First-level approval for branch-originated requests
- **Department Head** - Departmental approval for HQ requests or second-level for branches
- **Regional Manager** - Regional-level approval for large amounts
- **Group Finance Manager** - HQ finance approval
- **CFO** - Executive approval for high-value requests (Tier 4 mandatory)

**Action:** `approved` or `rejected`  
**Decision:** Business/operational judgment

### 2. **Treasury** (Validator & Payment Executor)
**Role:** Financial validation and payment execution

**Responsibilities:**
- ✅ Verify all required approvals are complete
- ✅ Validate account details and payment information
- ✅ Execute the actual payment
- ✅ Confirm payment completion
- ❌ Does NOT make approval decisions

**Action:** `validated` → `paid`  
**Position in workflow:** ALWAYS after all approvals, before FP&A review

**Why Treasury is last:**
- Separation of duties (approval ≠ payment)
- Financial controls and fraud prevention
- Ensures all approvals complete before funds disbursed

### 3. **FP&A** (Post-Payment Reviewer)
**Role:** Post-payment review and analysis

**Responsibilities:**
- Review payment for budget compliance
- Analyze spending patterns
- Flag anomalies for investigation
- Provide financial insights

**Action:** `reviewed`  
**Position in workflow:** ALWAYS last (after payment)

---

## Correct Workflow Sequences

### Tier 1: ≤ $10,000 (Routine)

**Branch Origin:**
```
Staff (creates) → Branch Manager (approves) → Treasury (validates & pays)
```

**HQ Origin:**
```
Staff (creates) → Department Head (approves) → Treasury (validates & pays)
```

**Roles:**
- 1 approver
- 1 validator/payer

---

### Tier 2: $10,001 - $50,000 (Departmental)

**Branch Origin:**
```
Staff → Branch Manager (approves) → Department Head (approves) → Treasury (validates & pays)
```

**HQ Origin:**
```
Staff → Department Head (approves) → Group Finance Manager (approves) → Treasury (validates & pays)
```

**Roles:**
- 2 approvers
- 1 validator/payer

---

### Tier 3: $50,001 - $250,000 (Regional)

**Branch Origin:**
```
Staff → Branch Manager (approves) → Regional Manager (approves) → Treasury (validates & pays) → FP&A (reviews)
```

**HQ Origin:**
```
Staff → Department Head (approves) → Group Finance Manager (approves) → Treasury (validates & pays) → FP&A (reviews)
```

**Roles:**
- 2 approvers
- 1 validator/payer
- 1 post-payment reviewer

---

### Tier 4: > $250,000 (HQ-Level, CFO Required)

**Branch Origin:**
```
Staff → Regional Manager (approves) → CFO (approves) → Treasury (validates & pays) → FP&A (reviews)
```

**HQ Origin:**
```
Staff → Group Finance Manager (approves) → CFO (approves) → Treasury (validates & pays) → FP&A (reviews)
```

**Roles:**
- 2 approvers (CFO mandatory)
- 1 validator/payer
- 1 post-payment reviewer

**Special Rules:**
- ❌ Cannot fast-track (even if urgent)
- ✅ CFO approval always required

---

## Urgent Fast-Track Logic

### How It Works
For Tier 1-3 urgent requests:
1. System identifies final step (Treasury)
2. **Skips all approvers** (not Treasury!)
3. Routes directly to Treasury for validation & payment

### Example: Tier 2 Urgent ($25,000)

**Normal Flow:**
```
Staff → BM (approves) → DH (approves) → Treasury (validates & pays)
```

**Urgent Fast-Track:**
```
Staff → Treasury (validates & pays)
```

**Key Points:**
- ✅ Approvers are skipped (BM, DH)
- ✅ Treasury step is NEVER skipped (financial control)
- ✅ Payment still requires Treasury validation
- ❌ Does NOT work for Tier 4 (high-value protection)

---

## Why This Matters

### 1. **Separation of Duties**
- **Approval** = Business decision ("Is this justified?")
- **Payment** = Financial execution ("Are the details correct?")
- Different people = Fraud prevention

### 2. **Audit Trail**
Clear distinction between:
- Who **authorized** the expenditure
- Who **validated** the payment details
- Who **executed** the payment
- Who **reviewed** post-payment

### 3. **Compliance**
- SOX compliance (financial controls)
- Internal audit requirements
- Fraud prevention best practices

---

## Status Progression

### Normal Tier 1-2 Flow
```
draft → pending → approved → validated → paid
```

### Tier 3-4 Flow (with FP&A)
```
draft → pending → approved → validated → paid → reviewed
```

### Urgent Flow (Tier 1-3)
```
draft → pending → validated → paid
```

---

## Common Misunderstandings (CORRECTED)

### ❌ WRONG: "Treasury is an approver"
**✅ CORRECT:** Treasury validates payment details and executes payment after approvals

### ❌ WRONG: "CFO comes after Treasury"
**✅ CORRECT:** CFO approves BEFORE Treasury validates & pays (Tier 4)

### ❌ WRONG: "Urgent requests skip all steps"
**✅ CORRECT:** Urgent requests skip approvers but ALWAYS go to Treasury for validation

### ❌ WRONG: "FP&A approves high-value requests"
**✅ CORRECT:** FP&A reviews AFTER payment for analysis (not approval)

---

## Implementation in Code

### ApprovalThreshold sequences:

```python
# Tier 4 Branch - CORRECT ORDER
'roles_sequence': ['regional_manager', 'cfo', 'treasury', 'fp&a']
#                   ↑ approve        ↑ approve  ↑ validate  ↑ review
#                                              & pay

# Tier 4 HQ - CORRECT ORDER
'roles_sequence': ['group_finance_manager', 'cfo', 'treasury', 'fp&a']
#                   ↑ approve              ↑ approve  ↑ validate  ↑ review
#                                                    & pay
```

### Actions in ApprovalTrail:
- `approved` - Used by approvers (BM, DH, RM, GFM, CFO)
- `validated` - Used by Treasury (before payment)
- `paid` - Payment executed by Treasury
- `reviewed` - Used by FP&A (post-payment)
- `rejected` - Can be used by any approver

---

## Summary

| Role | Phase | Action | Can Reject? |
|------|-------|--------|-------------|
| Branch Manager | Approval | `approved` | ✅ Yes |
| Department Head | Approval | `approved` | ✅ Yes |
| Regional Manager | Approval | `approved` | ✅ Yes |
| Group Finance Manager | Approval | `approved` | ✅ Yes |
| CFO | Approval | `approved` | ✅ Yes |
| **Treasury** | **Validation & Payment** | `validated` → `paid` | ✅ Yes (if invalid) |
| FP&A | Post-Payment Review | `reviewed` | ❌ No (post-payment) |

---

## Key Takeaways

1. 🎯 **Treasury = Validator & Payer**, not Approver
2. 📋 **Treasury always comes AFTER all approvals**
3. 💰 **Treasury executes payment** (changes status to `paid`)
4. 🔍 **FP&A reviews AFTER payment** (changes status to `reviewed`)
5. ⚡ **Urgent fast-track skips approvers**, never Treasury
6. 🔒 **Tier 4 CFO approves BEFORE Treasury** validates & pays

This ensures proper separation of duties and maintains financial controls! 🛡️
