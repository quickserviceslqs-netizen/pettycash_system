# Django Admin - Permission & Authorization Management Guide

## Overview

The Django Admin panel provides comprehensive tools for managing users, permissions, and role-based app access. Access it at: `/admin/`

---

## Features

### 1. **Enhanced User Management**

Navigate to **Users** in the admin panel to:

- **View User Details**: See display names, roles, assigned apps, and organizational hierarchy
- **Color-Coded Role Badges**: Visual role identification
- **App Access Display**: See which apps each user can access based on their role
- **Centralized Approver Management**: Mark users as centralized (company-wide) approvers

#### User List Columns:
- **Display Name**: Full name with username fallback
- **Role Badge**: Color-coded role display
- **Company/Branch/Department**: Organizational assignment
- **Accessible Apps**: Shows apps user can access (based on role)
- **Is Centralized Approver**: Company-wide approval permission
- **Is Staff/Active**: System access flags

#### Bulk Actions:
- **Activate/Deactivate Users**: Enable or disable user accounts
- **Make Centralized Approver**: Grant company-wide approval permissions
- **Remove Centralized Approver**: Revoke company-wide approval permissions

---

### 2. **Role-Based App Access**

App access is automatically determined by user role:

| Role                    | Accessible Apps                          | Can Approve |
|-------------------------|------------------------------------------|-------------|
| **Admin**               | transactions, treasury, workflow, reports| ✓           |
| **Staff**               | transactions                             | -           |
| **Treasury**            | treasury                                 | ✓           |
| **FP&A**                | transactions, reports                    | ✓           |
| **Department Head**     | workflow                                 | ✓           |
| **Branch Manager**      | workflow                                 | ✓           |
| **Regional Manager**    | workflow, reports                        | ✓           |
| **Group Finance Manager**| workflow, reports                       | ✓           |
| **CFO**                 | reports                                  | ✓           |
| **CEO**                 | reports                                  | -           |

---

### 3. **Permission Management**

#### User-Level Permissions
1. Go to **Users** → Select user → Scroll to **System Permissions**
2. Set permissions:
   - **Is Active**: User can log in
   - **Is Staff**: User can access admin panel
   - **Is Superuser**: User has all permissions
   - **Groups**: Assign to role-based groups
   - **User Permissions**: Granular permission assignment

#### Group-Level Permissions
1. Go to **Groups** to manage role-based permission sets
2. Each group corresponds to a role (e.g., "Role: Treasury")
3. Assign permissions to groups for easier management
4. Users automatically inherit group permissions

#### Permission Model
- View all available permissions in **Permissions** section
- Filter by content type (app)
- Search by name or codename

---

### 4. **Assigning Apps to Users**

**Method 1: Change User Role**
1. Go to **Users** → Select user
2. Change **Role** field in "Role & Organizational Hierarchy"
3. User automatically gets apps based on new role
4. Save changes

**Method 2: Custom Permissions (Advanced)**
1. Go to **Users** → Select user
2. Scroll to **System Permissions** section
3. Expand **User permissions** or **Groups**
4. Add specific app permissions manually
5. Save changes

**Method 3: Use Management Command**
```bash
# Sync all users to their role-based groups
python manage.py sync_role_permissions

# View current role access matrix
python manage.py show_role_access
```

---

### 5. **Organizational Hierarchy Assignment**

When editing a user, assign organizational context:

- **Company**: Which company the user belongs to
- **Region**: Geographic region (for regional managers)
- **Branch**: Specific branch (for branch-level users)
- **Department**: Department assignment
- **Cost Center**: Financial cost center
- **Position Title**: Job position

This hierarchy is used for:
- Workflow routing (approval chains)
- Data filtering (users see only their scope)
- Report generation

---

## Common Tasks

### Add New User
1. Click **Add User** in Users section
2. Enter username and password
3. Set email and role
4. Assign to company
5. Save

### Change User's App Access
1. Select user from list
2. Change **Role** to desired role
3. Save (apps update automatically)

### Make User a Company-Wide Approver
1. Select user from list
2. Check **Is centralized approver**
3. Save (user can now approve all company requisitions)

### Deactivate User Account
1. Select users from list
2. Choose **Deactivate selected users** action
3. Click **Go**

### Grant Admin Panel Access
1. Select user from list
2. Check **Is staff** in System Permissions
3. Save (user can now access /admin/)

### Create Role-Based Group
1. Go to **Groups**
2. Click **Add Group**
3. Name: "Role: [Role Name]"
4. Assign permissions from relevant apps
5. Save

### Sync All Users to Role Groups
```bash
python manage.py sync_role_permissions
```

---

## Security Best Practices

1. **Principle of Least Privilege**
   - Only grant necessary permissions
   - Use role-based access (not individual permissions)
   - Regularly review user permissions

2. **Centralized Approvers**
   - Use sparingly (breaks separation of duties)
   - Document why user needs company-wide approval rights
   - Monitor centralized approver activity

3. **Staff Access**
   - Only grant `is_staff` to users who need admin panel access
   - Reserve `is_superuser` for IT/system administrators only

4. **Regular Audits**
   - Review active users quarterly
   - Deactivate terminated employees immediately
   - Check for unused accounts

5. **Role Assignment**
   - Assign roles that match actual job function
   - Don't create "special case" roles
   - Use groups for custom permission sets

---

## Management Commands

### Show Role Access Matrix
```bash
python manage.py show_role_access
```
Displays which apps each role can access and which roles can approve.

### Sync Role Permissions
```bash
python manage.py sync_role_permissions
```
Creates role-based groups and assigns all users to their respective groups.

---

## Troubleshooting

### User Can't See Expected App
1. Check user's **Role** matches expected app access
2. Verify user **Is Active**
3. Check **Accessible Apps** column in user list
4. Run `python manage.py show_role_access` to verify role mapping

### User Can't Approve Requisitions
1. Verify role is in approver roles (see matrix above)
2. Check **Is Centralized Approver** if approval is cross-department
3. Verify organizational hierarchy (company/branch/department) matches requisition

### Permission Changes Not Applied
1. Log out and log back in
2. Clear browser cache
3. Run `python manage.py sync_role_permissions`
4. Check group assignments in user detail

### User Can't Access Admin Panel
1. Check **Is Staff** is enabled
2. Verify **Is Active** is enabled
3. User must have staff status to access /admin/

---

## Advanced: Custom Permission Setup

For complex permission requirements:

1. Create custom Group (e.g., "Treasury Analysts")
2. Assign specific permissions to group
3. Add users to this group
4. Users inherit group permissions + role permissions

Example:
```python
# In Django admin:
Groups → Add Group
Name: "Treasury Analysts"
Permissions: 
  - treasury | payment | Can add payment
  - treasury | payment | Can view payment
  - treasury | payment | Can execute payment
Save

# Then assign users to this group
Users → Select user → Groups → Add "Treasury Analysts"
```

---

## Support

For role access changes or new app assignments, contact the system administrator or modify `accounts/views.py` `ROLE_ACCESS` mapping.
