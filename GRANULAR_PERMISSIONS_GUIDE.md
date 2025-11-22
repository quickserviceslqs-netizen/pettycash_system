# Granular Permissions System - User Guide

## 🎯 Two-Level Access Control

Your system now has **TWO levels of control**:

### Level 1: App Access
**What:** Which applications can a user see?  
**How:** Assign apps to users in Django Admin  
**Examples:** Transactions, Treasury, Workflow, Reports

### Level 2: Permission Control
**What:** What can they do within those apps?  
**How:** Assign Django permissions (add, view, change, delete)  
**Examples:** Can add payments, can view reports, can change requisitions

---

## 📋 Step-by-Step: Assigning Access

### Step 1: Create/Edit User
1. Go to Django Admin → Users
2. Click on a user (or "Add User")

### Step 2: Assign Apps
In the **"App Access"** section:
- Select which apps this user can access
- Use Ctrl+Click to select multiple
- Available apps:
  - ✅ Transactions
  - ✅ Treasury
  - ✅ Workflow
  - ✅ Reports

### Step 3: Assign Permissions (Optional)
In the **"System Permissions"** section, scroll to "User permissions":

**Common permission patterns:**

**Treasury Staff Example:**
```
Apps: Treasury, Transactions
Permissions:
  ✅ treasury | payment | Can view payment
  ✅ treasury | payment | Can change payment
  ✅ treasury | payment | Can add payment
  ❌ treasury | payment | Can delete payment (usually restricted)
  ✅ transactions | requisition | Can view requisition
```

**Reports Viewer Example:**
```
Apps: Reports
Permissions:
  ✅ reports | report | Can view report
  ❌ reports | report | Can add report
  ❌ reports | report | Can change report
  ❌ reports | report | Can delete report
```

**Admin Example:**
```
Apps: All apps
Permissions:
  ✅ Select all relevant permissions
```

---

## 💡 Using Groups (Recommended for Teams)

Instead of assigning permissions to each user individually, use **Groups**:

### Create a Group
1. Django Admin → Groups → Add Group
2. Name it (e.g., "Treasury Team")
3. Assign permissions to the group
4. Add users to that group

**Example Groups:**

**Treasury Team Group:**
- Permissions: view/add/change payments, view requisitions
- Members: All treasury staff

**Report Viewers Group:**
- Permissions: view reports only
- Members: CEO, CFO, FP&A, Regional Managers

**Workflow Approvers Group:**
- Permissions: view/change requisitions (for approvals)
- Members: All managers and department heads

---

## 🔐 Permission Naming Convention

Django permissions follow this pattern:
```
app_label.codename

Examples:
  treasury.view_payment
  treasury.add_payment
  treasury.change_payment
  treasury.delete_payment
  
  transactions.view_requisition
  transactions.add_requisition
  transactions.change_requisition
  transactions.delete_requisition
```

---

## 👨‍💻 For Developers: Using Permissions in Code

### Method 1: Decorator (Recommended)
```python
from accounts.permissions import require_app_access, require_permission

# Check app access only
@require_app_access('treasury')
def payment_list(request):
    # User must have Treasury app assigned
    ...

# Check specific permission
@require_permission('treasury.change_payment')
def edit_payment(request, payment_id):
    # User must have permission to change payments
    ...

# Check both
@require_app_access('treasury')
@require_permission('treasury.add_payment')
def create_payment(request):
    # User must have Treasury app AND permission to add payments
    ...
```

### Method 2: In-View Check
```python
from accounts.permissions import check_permission

def my_view(request):
    if check_permission(request.user, 'change_payment', 'treasury'):
        # User can edit payments
        show_edit_button = True
    else:
        show_edit_button = False
```

### Method 3: Template Check
```django
{% if perms.treasury.change_payment %}
    <a href="{% url 'edit_payment' payment.id %}">Edit</a>
{% endif %}

{% if perms.treasury.delete_payment %}
    <button>Delete</button>
{% endif %}
```

---

## 📊 Common Scenarios

### Scenario 1: Treasury Staff
**Need:** Process payments but not delete them

**Setup:**
1. Assign App: Treasury
2. Assign Permissions:
   - ✅ treasury.view_payment
   - ✅ treasury.add_payment
   - ✅ treasury.change_payment
   - ❌ treasury.delete_payment

### Scenario 2: Department Head
**Need:** Approve requisitions only

**Setup:**
1. Assign App: Workflow
2. Assign Permissions:
   - ✅ transactions.view_requisition
   - ✅ transactions.change_requisition (for approvals)
   - ❌ transactions.add_requisition
   - ❌ transactions.delete_requisition

### Scenario 3: Report Viewer (CEO/CFO)
**Need:** View analytics only

**Setup:**
1. Assign App: Reports
2. Assign Permissions:
   - ✅ reports.view_report
   - ❌ reports.add_report
   - ❌ reports.change_report
   - ❌ reports.delete_report

### Scenario 4: Business Admin
**Need:** Full access to all apps

**Setup:**
1. Assign Apps: All (Transactions, Treasury, Workflow, Reports)
2. Option A: Make them superuser (is_superuser=True)
3. Option B: Create "Admin Group" with all permissions and add user to group

---

## 🚀 Migration from Role-Based to Permission-Based

### Backward Compatibility
The system still supports role-based access as a **fallback**:
- If a user has NO apps assigned → uses their role to determine apps
- This ensures existing users continue working

### Recommended Migration Path
1. **Phase 1:** Populate apps (already done via `populate_apps` command)
2. **Phase 2:** Start assigning apps to new users
3. **Phase 3:** Gradually assign apps to existing users
4. **Phase 4:** Once all users have apps assigned, you can remove ROLE_ACCESS mapping

### Quick Bulk Assignment (Future Enhancement)
Create a management command to auto-assign apps based on current roles:
```python
# Future: python manage.py migrate_roles_to_apps
```

---

## ✅ Best Practices

1. **Use Groups** - Easier to manage teams than individual users
2. **Principle of Least Privilege** - Give only the permissions needed
3. **Document Your Groups** - Keep notes on what each group is for
4. **Regular Audits** - Review who has access to what quarterly
5. **Test Permissions** - Login as different users to verify access
6. **App First, Permissions Second** - Assign apps, then fine-tune with permissions

---

## 🔍 Troubleshooting

**User can't see an app:**
- Check if app is assigned in "App Access" section
- Check if user's role has app in ROLE_ACCESS (fallback)
- Check if app is marked as active

**User can see app but can't do anything:**
- They have app access but no permissions
- Assign specific permissions or add to appropriate group

**User has permission but still gets error:**
- Check if permission check in code matches assigned permission
- Verify permission codename format (app_label.codename)

---

## 📖 Summary

**Old System:**
```
User.role → ROLE_ACCESS → Fixed apps per role
```

**New System:**
```
User → Assigned Apps → Which apps they see
       ↓
User → Django Permissions → What they can do in those apps
```

**Result:** Maximum flexibility with granular control! 🎯
