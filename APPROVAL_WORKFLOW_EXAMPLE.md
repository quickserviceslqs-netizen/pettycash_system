# Approval Workflow - Complete Example

## Overview

The Petty Cash System uses a **tiered approval workflow** based on:
- **Amount** - How much money is being requested
- **Origin Type** - Where the request comes from (Branch, HQ, Field)
- **User Roles** - Who needs to approve at each level

---

## Approval Tiers (Current Configuration)

| Tier | Amount Range | Required Approvers | Fast-Track Urgent? |
|------|--------------|-------------------|-------------------|
| **Tier 1** | $0 - $1,000 | Branch Manager | ✅ Yes |
| **Tier 2** | $1,000.01 - $10,000 | Branch Manager → Finance | ✅ Yes |
| **Tier 3** | $10,000.01 - $50,000 | Branch Manager → Finance → Treasury | ❌ No |

---

## Example 1: Small Purchase ($500)

### Scenario
**Sarah** (Staff, Operations Department) needs $500 for office supplies.

### Step-by-Step Flow

#### 1. **Sarah Creates Requisition**
- Logs in as `staff_user`
- Goes to "Requisitions" app
- Clicks "Create New Requisition"
- Fills form:
  ```
  Amount: $500
  Purpose: Office supplies - printer paper, pens, folders
  Origin: Branch
  Branch: Test Branch
  Department: Operations
  Urgent: No
  ```
- Clicks "Submit"

#### 2. **System Processes Request**
```
System checks amount ($500):
→ Falls into Tier 1 (0 - 1000)
→ Tier 1 requires: ['BRANCH_MANAGER']

System finds approvers:
→ Looks for users with role='branch_manager'
→ Filters by branch='Test Branch' (same as requester)
→ Excludes Sarah (no self-approval)
→ Finds: John Smith (branch_user)

System creates workflow:
→ workflow_sequence: [{"user_id": 123, "role": "BRANCH_MANAGER"}]
→ next_approver: John Smith
→ status: 'pending'
```

#### 3. **Requisition Status**
Sarah sees in her dashboard:
```
Requisition ID: REQ-7a8b9c
Amount: $500.00
Status: Pending
Next Approver: John Smith (Branch Manager)
Created: Nov 20, 2025 10:30 AM
```

#### 4. **John (Branch Manager) Receives Notification**
- Logs in as `branch_user`
- Dashboard shows: "1 Pending Approval"
- Clicks "Pending Approvals" section
- Sees Sarah's requisition:
  ```
  REQ-7a8b9c | $500.00 | Office supplies
  Requested by: Sarah (Staff)
  Branch: Test Branch
  Tier: Tier 1
  ```

#### 5. **John Reviews and Approves**
- Clicks on requisition to view details
- Reviews:
  - Amount: $500
  - Purpose: Office supplies
  - Department budget: OK
- Clicks "Approve" button
- Optionally adds comment: "Approved - within budget"

#### 6. **System Updates After Approval**
```
System checks workflow:
→ workflow_sequence has only 1 approver
→ This was the FINAL approval

System updates requisition:
→ status: 'reviewed' (fully approved!)
→ next_approver: NULL
→ workflow_sequence: []

System creates Payment record:
→ amount: $500
→ status: 'pending'
→ method: 'bank_transfer'
→ requisition: REQ-7a8b9c

System creates Approval Trail:
→ user: John Smith
→ role: BRANCH_MANAGER
→ action: 'approved'
→ comment: "Approved - within budget"
→ timestamp: Nov 20, 2025 10:45 AM
```

#### 7. **Sarah Gets Notification**
Dashboard updates:
```
Requisition REQ-7a8b9c
Status: Reviewed ✅
All approvals complete - awaiting payment
```

#### 8. **Treasury Processes Payment**
- **Mike** (Treasury Officer) logs in as `treasury_user`
- Dashboard shows: "1 Pending Payment"
- Clicks "Pending Payments"
- Sees:
  ```
  REQ-7a8b9c | $500.00 | Sarah (Staff)
  Purpose: Office supplies
  Approved by: John Smith
  Status: Ready to Execute
  ```
- Clicks "Execute Payment"
- Enters beneficiary details
- Confirms OTP (2-factor authentication)
- Payment executed ✅

#### 9. **Final Status**
```
Requisition: REQ-7a8b9c
Status: Paid
Amount: $500.00
Requested: Nov 20, 2025 10:30 AM
Approved: Nov 20, 2025 10:45 AM
Paid: Nov 20, 2025 11:00 AM

Approval Trail:
1. John Smith (Branch Manager) - Approved - Nov 20 10:45 AM

Payment Trail:
1. Mike Johnson (Treasury) - Executed - Nov 20 11:00 AM
```

---

## Example 2: Medium Purchase ($5,000)

### Scenario
**David** (Staff) needs $5,000 for equipment repair.

### Workflow Flow

#### 1. **David Creates Request**
```
Amount: $5,000
Purpose: Air conditioning unit repair
Origin: Branch
```

#### 2. **System Assigns Tier 2**
```
Tier 2: $1,000.01 - $10,000
Required approvers: ['BRANCH_MANAGER', 'FINANCE']

Workflow sequence:
1. John Smith (Branch Manager)
2. Lisa Chen (Finance Manager)
```

#### 3. **First Approval - Branch Manager**
- John approves on Nov 20, 10:30 AM
- Status: Still "Pending"
- Next approver: Lisa Chen (Finance)

```
System updates:
→ Removes John from workflow_sequence
→ next_approver: Lisa Chen
→ status: 'pending' (not done yet!)
```

#### 4. **Second Approval - Finance Manager**
- Lisa reviews on Nov 20, 2:00 PM
- Checks budget allocation
- Approves request
- Status changes to "Reviewed"

```
System updates:
→ workflow_sequence: [] (empty - all done!)
→ next_approver: NULL
→ status: 'reviewed'
→ Creates Payment record
```

#### 5. **Treasury Executes**
- Mike executes payment
- $5,000 transferred
- Status: "Paid" ✅

### Timeline
```
Nov 20, 10:00 AM - David creates request
Nov 20, 10:30 AM - John (Branch Manager) approves
Nov 20, 2:00 PM  - Lisa (Finance) approves
Nov 20, 2:30 PM  - Mike (Treasury) executes payment
Status: COMPLETE
```

---

## Example 3: Large Purchase ($25,000)

### Scenario
**Emma** (Department Head) needs $25,000 for new computers.

### Workflow Flow

#### Tier 3: Three Approvers Required
```
Amount: $25,000
Tier: Tier 3 ($10,000.01 - $50,000)
Approvers: ['BRANCH_MANAGER', 'FINANCE', 'TREASURY']

Workflow sequence:
1. John Smith (Branch Manager)
2. Lisa Chen (Finance Manager)  
3. Mike Johnson (Treasury Manager)
```

#### Approval Chain
```
Step 1: Branch Manager approves
→ Status: Pending
→ Next: Finance Manager

Step 2: Finance Manager approves
→ Status: Pending
→ Next: Treasury Manager

Step 3: Treasury Manager approves
→ Status: Reviewed (FINAL!)
→ Creates Payment record
→ Treasury can now execute payment
```

---

## Example 4: Urgent Request (Fast-Track)

### Scenario
**Sarah** needs $800 urgently for emergency repair.

### Special Handling

#### 1. **Create Urgent Request**
```
Amount: $800
Purpose: Emergency plumbing repair - office flooded
Origin: Branch
Urgent: ✅ YES
Urgency Reason: Water damage, immediate repair needed
```

#### 2. **System Fast-Tracks**
```
Normal Tier 1: Branch Manager only
Urgent Tier 1: Still Branch Manager (already single approver)

Note: Fast-track skips to final approver
Tier 1 has only 1 approver, so no change
```

#### 3. **For Tier 2 Urgent ($5,000)**
```
Normal: Branch Manager → Finance
Urgent: Skips directly to Finance ⚡

System creates workflow:
→ workflow_sequence: [{"user_id": 456, "role": "FINANCE"}]
→ Skips Branch Manager
→ Finance can approve immediately
```

---

## Special Cases

### Case 1: Self-Approval Prevention
```
Scenario: Branch Manager creates requisition

David (Branch Manager) creates $500 request
→ System needs Branch Manager approval
→ System excludes David (requester)
→ System escalates to Admin/Superuser

Workflow:
→ next_approver: Admin User
→ Prevents conflict of interest
```

### Case 2: No Approver Available
```
Scenario: No Finance Manager exists

Request needs Finance approval
→ System searches for role='finance'
→ No user found
→ Auto-escalates to Admin

Workflow:
→ Adds admin to workflow
→ Marks as 'auto_escalated': True
→ Tracks skipped role in audit trail
```

### Case 3: Treasury User Creates Request
```
Special rule: Treasury requests bypass normal workflow

Mike (Treasury) creates $1,500 request
→ Normal Tier 2: Branch Manager → Finance
→ Treasury override: Department Head → Group Finance Manager

Prevents treasury from approving their own payments
```

---

## Key Rules

### 1. **No Self-Approval**
- Requester cannot be in their own approval workflow
- System automatically excludes requester when finding approvers

### 2. **Sequential Approval**
- Approvers must approve in order
- Cannot skip levels (except urgent fast-track)
- Each approval moves to next person

### 3. **Role-Based, Not Person-Based**
- Workflow defined by roles, not specific users
- System finds appropriate person for each role
- Handles role changes automatically

### 4. **Scope Filtering**
- Branch requests → Branch managers only
- HQ requests → HQ managers
- Field requests → Regional managers
- Centralized roles (Treasury, CFO) → Company-wide

### 5. **Status Progression**
```
draft → pending → reviewed → paid
              ↓
           rejected (if denied)
```

---

## Dashboard Views

### Staff User Dashboard
```
My Requisitions (5)
- REQ-001 | $500  | Pending      | Awaiting: John Smith
- REQ-002 | $1,200| Reviewed     | Ready for payment
- REQ-003 | $300  | Paid         | Completed Nov 15
- REQ-004 | $850  | Rejected     | Denied by manager
- REQ-005 | $2,000| Pending      | Awaiting: Lisa Chen

[+ Create New Requisition]
```

### Branch Manager Dashboard
```
Pending Approvals (3)
- REQ-006 | $500  | Sarah   | Office supplies
- REQ-007 | $750  | David   | Training materials
- REQ-008 | $1,000| Emma    | Team lunch

My Requisitions (2)
- REQ-009 | $5,000| Pending | Awaiting: Finance

[+ Create New Requisition]
```

### Treasury Dashboard
```
Pending Payments (4)
- REQ-002 | $1,200 | Sarah  | Approved by: John, Lisa
- REQ-010 | $800   | David  | Approved by: John
- REQ-011 | $5,000 | Emma   | Approved by: John, Lisa
- REQ-012 | $300   | Mike   | Approved by: Admin

[Execute Payments]

Recent Payments (Last 7 days)
Total: $12,450 | Count: 8 payments
```

---

## API Workflow

### 1. Create Requisition
```http
POST /api/requisitions/
Authorization: Bearer <token>

{
  "amount": "500.00",
  "purpose": "Office supplies",
  "origin_type": "branch",
  "branch_id": 1,
  "department_id": 2,
  "is_urgent": false
}

Response:
{
  "transaction_id": "REQ-7a8b9c",
  "status": "pending",
  "next_approver": {
    "id": 123,
    "name": "John Smith",
    "role": "branch_manager"
  },
  "workflow_sequence": [
    {"user_id": 123, "role": "BRANCH_MANAGER"}
  ],
  "tier": "Tier 1"
}
```

### 2. Approve Requisition
```http
POST /transactions/approve/<requisition_id>/
Authorization: Bearer <token>

{
  "comment": "Approved - within budget"
}

Response:
→ Moves to next approver OR
→ Status: "reviewed" if final approval
```

### 3. Check Pending Approvals
```http
GET /api/requisitions/?next_approver=me&status=pending
Authorization: Bearer <token>

Response:
[
  {
    "transaction_id": "REQ-001",
    "amount": "500.00",
    "requested_by": "Sarah Johnson",
    "purpose": "Office supplies",
    "created_at": "2025-11-20T10:30:00Z"
  }
]
```

---

## Summary

**The approval system ensures:**
- ✅ Financial controls based on amount
- ✅ Proper authorization hierarchy
- ✅ No conflicts of interest
- ✅ Audit trail of all approvals
- ✅ Automatic routing to right approvers
- ✅ Transparency for requesters
- ✅ Efficient urgent request handling
- ✅ Treasury segregation of duties

**All approval decisions are logged, timestamped, and traceable!**
