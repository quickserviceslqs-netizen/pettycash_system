# Dashboard Issues - Fixed & Explained

## Issues Reported

1. ✅ **Staff member seeing "Pending Approvals" section** - FIXED
2. ⚠️ **"Staff Staff" duplicate text** - EXPLAINED (test data)
3. ❓ **Staff member being logged out when accessing requisitions** - NEEDS INVESTIGATION

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

## 2. "Staff Staff" Text (EXPLAINED ⚠️)

### What You're Seeing:
When logged in as `staff_user`, you might see "Staff Member" or "Staff Staff" displayed.

### Why This Happens:
The test data loader creates a user with:
- **First Name:** "Staff"
- **Last Name:** "Member"  
- **Role:** "staff"

Different UI areas show different information:
- **Header Badge:** Shows `role` = "staff"
- **Dashboard Welcome:** Shows `first_name last_name` = "Staff Member"

### This is NOT a bug - it's just test data!

**Real user example:**
- First Name: "John", Last Name: "Doe", Role: "staff"
- Display: "John Doe" + badge "staff" ✅ Looks perfect!

**Test user example:**
- First Name: "Staff", Last Name: "Member", Role: "staff"
- Display: "Staff Member" + badge "staff" ⚠️ Looks redundant

### Solution:
When creating real users in production, use actual names!

---

## 3. Requisitions Access Issue (NEEDS INVESTIGATION ❓)

### Problem Reported:
"Staff member gets logged out when trying to access requisitions app"

### Possible Causes:

**A. Permission Check (Most Likely)**
The requisitions view might have role-based permissions that block STAFF role.

**B. Session Timeout**
Idle sessions expire and redirect to login.

**C. CSRF Token Issue**
Missing token on form submission.

### Investigation Needed:

1. **Check Render logs:**
   - Go to https://dashboard.render.com → Your service → Logs
   - Look for errors when staff_user accesses `/transactions/`
   - Filter for "Permission" or "403" or "401"

2. **Check transactions/views.py:**
   - Look for role-based permission checks
   - See if STAFF is excluded from allowed roles

3. **Test with other roles:**
   - Try with `branch_user` (BRANCH_MANAGER)
   - Try with `finance_user` (FP&A)
   - See if they can access requisitions

### Temporary Workaround:
Use `branch_user`, `finance_user`, or `treasury_user` to test requisitions until we fix staff permissions.

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
