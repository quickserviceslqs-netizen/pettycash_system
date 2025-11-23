# 📤 Bulk User Import Guide

## Overview
Import multiple users at once via CSV upload instead of creating invitations one by one.

---

## 🚀 Quick Start

### 1. Access Bulk Import
```
/accounts/bulk-import/
```
Or click **"Bulk Import"** button on the Invitations page.

### 2. Download Template
Click **"Download Template"** to get `user_import_template.csv` with:
- Header row with field names
- Example data rows
- Instructions

### 3. Fill Template
Open CSV in Excel/Google Sheets and add user data:

```csv
email,first_name,last_name,role,company_name,department_name,branch_name,assigned_apps
john.doe@example.com,John,Doe,REQUESTER,Quick Services LQS,Finance,Head Office,treasury,workflow
jane.smith@example.com,Jane,Smith,APPROVER,Quick Services LQS,Finance,Head Office,treasury,workflow,reports
```

### 4. Upload File
- Delete example rows before uploading
- Upload completed CSV file
- System processes all rows
- Shows success/error report

---

## 📋 CSV Template Fields

| Field | Required | Format | Example |
|-------|----------|--------|---------|
| `email` | ✅ Yes | Valid email | `john.doe@example.com` |
| `first_name` | ✅ Yes | Text | `John` |
| `last_name` | ✅ Yes | Text | `Doe` |
| `role` | ✅ Yes | REQUESTER/APPROVER/FINANCE/ADMIN | `REQUESTER` |
| `company_name` | No | Must exist in system | `Quick Services LQS` |
| `department_name` | No | Must exist in system | `Finance` |
| `branch_name` | No | Must exist in system | `Head Office` |
| `assigned_apps` | No | Comma-separated app names | `treasury,workflow,reports` |

---

## 🎯 Username Auto-Generation

**Format:** `FirstnameLastname` (no spaces)

### Examples:
- John Doe → `JohnDoe`
- Jane Smith → `JaneSmith`
- Mary-Ann O'Connor → `MaryAnnOConnor`

### Duplicate Handling:
If username exists, adds number suffix:
- First: `JohnDoe`
- Second: `JohnDoe1`
- Third: `JohnDoe2`

---

## ✅ Validation Rules

### Automatic Checks:
1. **Email Validation**
   - Must be valid email format
   - Cannot already exist in system
   - Cannot have pending invitation

2. **Role Validation**
   - Must be: REQUESTER, APPROVER, FINANCE, or ADMIN
   - Case-insensitive (accepts `requester`, `REQUESTER`, etc.)

3. **Organization Validation**
   - Company must exist in database
   - Department must exist in database
   - Branch must exist in database

4. **App Validation**
   - Apps are comma-separated
   - Invalid app names are skipped (not rejected)

---

## 📧 What Happens After Upload

### For Each Valid Row:
1. ✅ Creates `UserInvitation` record
2. ✅ Generates unique token
3. ✅ Sends invitation email to user
4. ✅ Email contains signup link
5. ✅ User receives username preview (FirstLast)

### User Receives Email:
```
Subject: Invitation to join Quick Services LQS

Hello John,

You've been invited to join as a Requester.

Click here to complete your registration:
https://yoursite.com/accounts/signup/abc-123-token/

Your username will be auto-generated as: JohnDoe
You will set your password during registration.

This invitation expires on December 01, 2024 at 10:30 AM.
```

---

## ⚠️ Common Errors

### Upload Errors & Solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| `Row 5: Missing required fields` | Empty email/name/role | Fill all required fields |
| `Row 8: Invalid role 'USER'` | Wrong role value | Use REQUESTER/APPROVER/FINANCE/ADMIN |
| `Row 10: User with email already exists` | Duplicate email | Remove duplicate row |
| `Row 12: Company 'ABC Corp' not found` | Org doesn't exist | Create org first or fix spelling |
| `Row 15: Pending invitation already exists` | Email invited before | Revoke old invitation first |

### Success Report Example:
```
✅ Successfully created 8 invitation(s)
⚠️ 2 row(s) failed. See details below.

❌ Row 5: Company 'Wrong Name' not found
❌ Row 12: User with email admin@example.com already exists
```

---

## 🔒 Security Features

### Built-in Protection:
1. **Permission Check:** Only users with `add_userinvitation` permission
2. **Duplicate Prevention:** Checks existing users and pending invitations
3. **Email Validation:** Prevents fake/invalid emails
4. **Organization Validation:** Prevents wrong hierarchy assignments
5. **Audit Trail:** Logs who imported and when

### Activity Log:
```
User: admin
Action: USER_BULK_IMPORT
Description: Bulk imported 15 user invitations
Timestamp: 2024-11-23 14:30:00
```

---

## 📊 Best Practices

### Before Upload:
1. ✅ **Verify Organizations Exist**
   - Check company/department/branch names match exactly
   - Create missing organizations first

2. ✅ **Use Correct Role Values**
   - REQUESTER - Basic users who create requests
   - APPROVER - Users who approve requests
   - FINANCE - Finance team members
   - ADMIN - System administrators

3. ✅ **Clean Email List**
   - Remove duplicates
   - Verify email addresses
   - Use corporate email domain

4. ✅ **Test Small Batch First**
   - Upload 2-3 users first
   - Verify invitation emails sent
   - Test signup process
   - Then upload full list

### After Upload:
1. ✅ **Review Success Report**
   - Check how many succeeded
   - Review error messages
   - Fix errors and re-upload failed rows

2. ✅ **Notify Users**
   - Let users know to check email
   - Provide support contact
   - Share username format info

3. ✅ **Monitor Signups**
   - Check invitation status page
   - Follow up on expired invitations
   - Resend if needed

---

## 🎓 Example Use Cases

### Scenario 1: New Department (10 Users)
```csv
email,first_name,last_name,role,company_name,department_name,branch_name,assigned_apps
user1@company.com,Alice,Johnson,REQUESTER,Quick Services LQS,Marketing,Head Office,treasury
user2@company.com,Bob,Williams,REQUESTER,Quick Services LQS,Marketing,Head Office,treasury
user3@company.com,Carol,Brown,APPROVER,Quick Services LQS,Marketing,Head Office,treasury,workflow
...
```

### Scenario 2: Mixed Roles
```csv
email,first_name,last_name,role,company_name,department_name,branch_name,assigned_apps
requester@co.com,John,Doe,REQUESTER,Quick Services LQS,Finance,Head Office,treasury
approver@co.com,Jane,Smith,APPROVER,Quick Services LQS,Finance,Head Office,treasury,workflow
finance@co.com,Bob,Jones,FINANCE,Quick Services LQS,Finance,Head Office,treasury,workflow,reports
admin@co.com,Alice,White,ADMIN,Quick Services LQS,Finance,Head Office,treasury,workflow,reports,settings
```

### Scenario 3: Multiple Branches
```csv
email,first_name,last_name,role,company_name,department_name,branch_name,assigned_apps
user1@co.com,Tom,Green,REQUESTER,Quick Services LQS,Sales,New York,treasury
user2@co.com,Sam,Blue,REQUESTER,Quick Services LQS,Sales,Los Angeles,treasury
user3@co.com,Pat,Red,REQUESTER,Quick Services LQS,Sales,Chicago,treasury
```

---

## 🔧 Troubleshooting

### Q: Template not downloading?
**A:** Check browser popup blocker. Try different browser.

### Q: CSV upload fails immediately?
**A:** Ensure file is `.csv` format, not `.xlsx`. Save as CSV in Excel.

### Q: All rows fail with "Company not found"?
**A:** Company name must match exactly (case-sensitive). Check spelling and spaces.

### Q: Some emails don't send?
**A:** Check SMTP settings in Django settings. Verify email server is working.

### Q: Usernames look wrong?
**A:** Usernames auto-generate from first/last name. Format is `FirstLast` with no spaces.

### Q: Can I change username after import?
**A:** No. Usernames are permanent. Names can be changed by admin but username stays same.

### Q: How to handle duplicate usernames?
**A:** System automatically adds number suffix (JohnDoe1, JohnDoe2). No action needed.

---

## 📝 Quick Reference

### Available Roles:
- `REQUESTER` - Create requisitions
- `APPROVER` - Approve requisitions  
- `FINANCE` - Finance operations
- `ADMIN` - System administration

### Available Apps (example):
- `treasury` - Treasury Management
- `workflow` - Workflow/Approvals
- `reports` - Reporting
- `settings` - Settings Management

### Important URLs:
- Bulk Import: `/accounts/bulk-import/`
- Download Template: `/accounts/download-template/`
- Manage Invitations: `/accounts/invitations/`

### Permissions Required:
- `accounts.add_userinvitation` - Required for bulk import

---

## 📞 Support

### Getting Help:
1. Check error messages in upload report
2. Review this guide for common issues
3. Contact system administrator
4. Check Django admin for organization names

### Reporting Issues:
Include in your report:
- CSV file (or sample rows)
- Error messages shown
- Number of rows uploaded
- Screenshot of error page

---

**Last Updated:** November 2024  
**Version:** 2.0
