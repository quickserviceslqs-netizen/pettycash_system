# Role-Based Access Control System

## Overview
This application uses **application roles** for access control, NOT Django's built-in permission system.

## 🎯 Access Control Strategy

### ✅ What We Use: Application Roles
- Defined in `User.role` field with `ROLE_CHOICES`
- Controlled via `ROLE_ACCESS` dictionary in `accounts/views.py`
- Simple, fast, and business-logic focused

### ❌ What We DON'T Use: Django Permissions
- Django permissions (`user.has_perm()`) are **NOT used** for business logic
- Django groups are **NOT needed**
- Permissions are ignored except for Django Admin access control

---

## 🔐 Two Separate Systems

### 1. Django Admin Access (Technical)
**Purpose:** Database management interface at `/admin/`

**Access Control:**
```python
is_staff = True      # Can login to Django Admin
is_superuser = True  # Has all Django Admin permissions (optional)
```

**Who needs this:**
- Technical administrators
- IT staff managing the database
- Business admins who need to create/modify users

**Note:** This is Django's built-in system, separate from business workflows.

---

### 2. User Dashboard Access (Business)
**Purpose:** Business application at `/dashboard/` and all business apps

**Access Control:**
```python
# Defined in accounts/views.py
ROLE_ACCESS = {
    "admin": ["transactions", "treasury", "workflow", "reports"],
    "staff": ["transactions"],
    "treasury": ["treasury", "workflow", "transactions"],
    "fp&a": ["transactions", "reports"],
    "department_head": ["workflow"],
    "branch_manager": ["workflow"],
    "regional_manager": ["workflow", "reports"],
    "group_finance_manager": ["workflow", "reports"],
    "cfo": ["reports"],
    "ceo": ["reports"],
}
```

**How it works:**
1. User logs in → redirected to dashboard
2. System checks `user.role`
3. Looks up `ROLE_ACCESS[user.role]` to get allowed apps
4. Shows navigation only for allowed apps
5. Each view checks `user.role` before allowing actions

---

## 📋 Role Definitions

| Role | Apps Access | Purpose |
|------|-------------|---------|
| **admin** | All apps | Business escalations, emergency approvals, full oversight |
| **staff** | Transactions only | Create requisitions, view own transactions |
| **treasury** | Treasury, Workflow, Transactions | Process payments, validate requisitions |
| **fp&a** | Transactions, Reports | Financial planning, analytics |
| **department_head** | Workflow | Approve department requisitions |
| **branch_manager** | Workflow | Approve branch requisitions |
| **regional_manager** | Workflow, Reports | Approve regional requisitions, view reports |
| **group_finance_manager** | Workflow, Reports | Approve group-level requisitions |
| **cfo** | Reports | Strategic oversight, financial reports |
| **ceo** | Reports | Executive oversight, company-wide reports |

---

## 🛡️ Permission Checks in Code

### ❌ DON'T Use Django Permissions
```python
# WRONG - We don't use this pattern
if not user.has_perm('treasury.change_payment'):
    return HttpResponseForbidden()
```

### ✅ DO Use Application Roles
```python
# CORRECT - Check application role
user_role = request.user.role.lower() if request.user.role else ''
if user_role not in ['treasury', 'admin']:
    messages.error(request, "You don't have permission")
    return redirect('dashboard')
```

### ✅ DO Use ROLE_ACCESS for Navigation
```python
# CORRECT - Get allowed apps
user_role = user.role.lower().strip()
apps = ROLE_ACCESS.get(user_role, [])
navigation = [{"name": app.capitalize(), "url": f"/{app}/"} for app in apps]
```

---

## 🔄 Managing Access

### To Give a User Access to an App:
1. Go to Django Admin → Users
2. Find the user
3. Change their **Role** field to appropriate role
4. System automatically grants app access based on ROLE_ACCESS mapping

### To Create Custom Access:
Edit `ROLE_ACCESS` dictionary in `accounts/views.py`:
```python
ROLE_ACCESS = {
    "my_custom_role": ["transactions", "reports"],  # Add your mapping
    # ... other roles
}
```

### To Remove Access:
Change user's role to one with less access, or remove apps from their role's mapping.

---

## 🎓 Best Practices

1. **Never use Django permissions in business views** - stick to role checks
2. **Keep ROLE_ACCESS centralized** - don't scatter role checks throughout codebase
3. **Use descriptive role names** - make it clear what each role does
4. **Document role changes** - update this file when adding new roles
5. **Principle of least privilege** - give users only the access they need

---

## 🚀 Advantages of This System

✅ **Simple**: One role field, one dictionary lookup  
✅ **Fast**: No database queries for permissions  
✅ **Clear**: Easy to understand who has access to what  
✅ **Maintainable**: All access rules in one place  
✅ **Business-focused**: Roles match business hierarchy  
✅ **Audit-friendly**: Role changes are clearly logged  

---

## 📝 Summary

**Django Permissions** → Only for Django Admin (`/admin/`)  
**Application Roles** → For all business logic and user dashboard  

Keep them separate, keep them simple! 🎯
