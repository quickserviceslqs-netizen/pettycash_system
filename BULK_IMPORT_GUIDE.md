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

**Updated Format (v2.1):**
```csv
email,first_name,last_name,role,company_name,region_name,branch_name,department_name,assigned_apps
amos.cheloti@company.com,Amos,Cheloti,REQUESTER,Quick Services LQS,East Africa,Nairobi Branch,Finance,treasury,workflow
jane.doe@company.com,Jane,Doe,APPROVER,Quick Services LQS,East Africa,Mombasa Branch,Finance,treasury,workflow,reports
```

**Note:** Column order changed to group organizational hierarchy logically.

### 4. Upload File
- Delete example rows before uploading
- Upload completed CSV file
- System processes all rows
- Shows success/error report

---

## 📋 CSV Template Fields

| Field | Required | Format | Example |
|-------|----------|--------|---------|
| `email` | ✅ Yes | Valid email | `amos.cheloti@company.com` |
| `first_name` | ✅ Yes | Text | `Amos` |
| `last_name` | ✅ Yes | Text | `Cheloti` |
| `role` | ✅ Yes | REQUESTER/APPROVER/FINANCE/ADMIN | `REQUESTER` |
| `company_name` | No | Must EXACTLY match existing | `Quick Services LQS` |
| `region_name` | No | Region name (for branch filtering) | `East Africa` |
| `branch_name` | No | Must EXACTLY match existing | `Nairobi Branch` |
| `department_name` | No | Must EXACTLY match existing | `Finance` |
| `assigned_apps` | No | Comma-separated app names | `treasury,workflow,reports` |

**Important:** Company, Region, Branch, Department names are **case-sensitive** and must match EXACTLY.

---

## 🗺️ Multi-Company / Multi-Branch / Multi-Region Support

### Organization Hierarchy:
```
Company
  └── Region
       └── Branch
            └── Department
```

### How It Works:

1. **Download Template** - Includes complete list of ALL organizations
2. **Find Your Organizations** - Scroll to "AVAILABLE ORGANIZATIONS" section in CSV
3. **Copy Exact Names** - Copy company/branch/department names exactly (case-sensitive)
4. **Use Region Filter** - Specify region if multiple branches have same name

### Example CSV with Multi-Branch:

```csv
email,first_name,last_name,role,company_name,region_name,branch_name,department_name,assigned_apps
user1@co.com,Amos,Cheloti,REQUESTER,Quick Services LQS,East Africa,Nairobi Branch,Finance,treasury
user2@co.com,Jane,Doe,APPROVER,Quick Services LQS,East Africa,Mombasa Branch,Operations,treasury,workflow
user3@co.com,Bob,Smith,FINANCE,ABC Corporation,West Africa,Lagos Branch,Finance,treasury,reports
```

**Result:**
- Amos → Company: Quick Services LQS, Region: East Africa, Branch: Nairobi
- Jane → Company: Quick Services LQS, Region: East Africa, Branch: Mombasa
- Bob → Company: ABC Corporation, Region: West Africa, Branch: Lagos

### When to Use `region_name`:

✅ **Use region when:**
- Multiple branches have the same name (e.g., "Head Office" in different regions)
- You want to ensure correct branch mapping
- Template shows multiple matches for branch name

❌ **Skip region when:**
- Branch name is unique across all regions
- Only one branch with that name exists

---

## 🎯 Username Auto-Generation

**Format:** `FirstInitial.LastName` (Professional corporate standard)

### Examples:
- Amos Cheloti → `A.Cheloti`
- Jane Doe → `J.Doe`
- Mary-Ann O'Connor → `M.OConnor`
- John Smith → `J.Smith`

### Duplicate Handling:
If username exists, adds number suffix:
- First: `A.Cheloti`
- Second: `A.Cheloti1`
- Third: `A.Cheloti2`

**Why This Format?**
- ✅ Professional and concise
- ✅ Easy to type and remember
- ✅ Industry standard (Initial.Surname)
- ✅ Handles duplicates cleanly

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
email,first_name,last_name,role,company_name,region_name,branch_name,department_name,assigned_apps
alice.j@co.com,Alice,Johnson,REQUESTER,Quick Services LQS,East Africa,Nairobi Branch,Marketing,treasury
bob.w@co.com,Bob,Williams,REQUESTER,Quick Services LQS,East Africa,Nairobi Branch,Marketing,treasury
carol.b@co.com,Carol,Brown,APPROVER,Quick Services LQS,East Africa,Nairobi Branch,Marketing,treasury,workflow
```

**Result:** Usernames will be `A.Johnson`, `B.Williams`, `C.Brown`

### Scenario 2: Multi-Company Setup
```csv
email,first_name,last_name,role,company_name,region_name,branch_name,department_name,assigned_apps
amos.c@qslqs.com,Amos,Cheloti,REQUESTER,Quick Services LQS,East Africa,Nairobi Branch,Finance,treasury
jane.d@abc.com,Jane,Doe,APPROVER,ABC Corporation,West Africa,Lagos Branch,Finance,treasury,workflow
bob.j@xyz.com,Bob,Jones,FINANCE,XYZ Limited,Central Africa,Kampala Branch,Finance,treasury,reports
```

**Result:** Three different companies, three different regions, usernames: `A.Cheloti`, `J.Doe`, `B.Jones`

### Scenario 3: Same Branch Name, Different Regions
```csv
email,first_name,last_name,role,company_name,region_name,branch_name,department_name,assigned_apps
tom.g@co.com,Tom,Green,REQUESTER,Quick Services LQS,East Africa,Head Office,Sales,treasury
sam.b@co.com,Sam,Blue,REQUESTER,Quick Services LQS,West Africa,Head Office,Sales,treasury
pat.r@co.com,Pat,Red,REQUESTER,Quick Services LQS,Central Africa,Head Office,Sales,treasury
```

**Result:** Same company, same branch name ("Head Office"), but different regions. Region filter ensures correct mapping.

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
