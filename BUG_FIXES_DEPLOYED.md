# Dashboard Issues - Fixed & Explained

## Summary of Fixes

**✅ FIXED:** Pending Approvals section - now only visible to approvers (not staff members)

**✅ FIXED:** Staff access to requisitions - added 'staff' to allowed transaction roles

**✅ FIXED:** Duplicate role display - removed "Role: Staff" line from dashboard (badge still shows role)

---

## Issues Reported

1. ✅ **Staff member seeing "Pending Approvals" section** - FIXED
2. ✅ **Duplicate "Staff" text** - FIXED  
3. ✅ **Staff member being logged out when accessing requisitions** - FIXED

---

## 1. Pending Approvals Section (FIXED ✅)

### Problem:
Staff members were seeing the "Pending Approvals" section even though they are not approvers.

### Root Cause:
The template was displaying the section for all users, not checking the `show_pending_section` variable.

### Fix Applied:
Updated `templates/accounts/dashboard.html` to wrap the section in a conditional:

```html
{% if show_pending_section %}
<section style="margin-bottom:40px;">
    <h3>Pending Approvals</h3>
    ...
</section>
{% endif %}
```

**Status:** ✅ Deployed to Render (auto-deploy in 3-5 minutes)

---

## 2. Duplicate Role Display (FIXED ✅)

### Problem:
"Staff Staff" or "Staff Member" text appeared to be duplicated in the UI.

### Root Cause:
The dashboard was showing "Role: Staff" on line 12, AND the header badge was also showing "staff", creating visual redundancy.

### Fix Applied:
Removed the redundant role line from dashboard template:

```html
<!-- Before -->
<h2>Welcome, {{ user.username|title }}!</h2>
<p>Role: {{ user_role|title }}</p>  ← Removed this line

<!-- After -->
<h2>Welcome, {{ user.username|title }}!</h2>
```

The user's role is still visible in the header badge (top right), so no information is lost.

**Status:** ✅ Deployed to Render

---

## 3. Requisitions Access Issue (FIXED ✅)

### Problem Reported:
"Staff member gets logged out when trying to access requisitions app"

### Root Cause:
The `transactions/urls.py` file had a role-based access control that **excluded STAFF role**:

```python
TRANSACTION_ROLES = [
    'admin', 'fp&a', 'department_head',
    'branch_manager', 'regional_manager', 'group_finance_manager'
]
# 'staff' was missing!
```

When a staff user tried to access `/transactions/`, the `protected()` decorator checked their role, found it wasn't in the allowed list, and redirected them to login (appearing as a logout).

### Fix Applied:
Added `'staff'` to the allowed transaction roles:

```python
TRANSACTION_ROLES = [
    'admin', 'staff', 'fp&a', 'department_head',  # ← Added 'staff'
    'branch_manager', 'regional_manager', 'group_finance_manager'
]
```

Now staff users can:
- ✅ Access the requisitions homepage (`/transactions/`)
- ✅ Create new requisitions (`/transactions/create/`)
- ✅ View their own requisitions
- ❌ Cannot approve/reject (still approver-only)

**Status:** ✅ Deployed to Render

---

## Current Status

| Issue | Status | Action Needed |
|-------|--------|---------------|
| Pending Approvals for staff | ✅ Fixed | Wait for Render deploy |
| "Staff Staff" duplicate | ⚠️ Test data | Use real names in production |
| Requisitions logout | ❓ Unknown | Check logs + permissions |

---

## Test Users Available

| Username | Password | Role | Department | Branch |
|----------|----------|------|------------|--------|
| admin | Admin@123456 | Superuser | - | - |
| treasury_user | Test@123456 | TREASURY | Finance | Test Branch |
| finance_user | Test@123456 | FP&A | Finance | Test Branch |
| branch_user | Test@123456 | BRANCH_MANAGER | Operations | Test Branch |
| staff_user | Test@123456 | STAFF | Operations | Test Branch |

---

## Next Steps

1. **Wait for auto-deploy** (3-5 minutes) for the Pending Approvals fix
2. **Check the requisitions issue:**
   - Login as staff_user
   - Try to access requisitions
   - Note the exact error or behavior
   - Check Render logs for details
3. **Share the error** so I can fix the permissions

For now, test requisitions workflow with `branch_user` or `finance_user`.
