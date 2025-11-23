# 📝 Onboarding Data Collection Guide

## Overview
This guide explains **what data should be collected during user onboarding**, optimizing for both **security** and **user experience**.

---

## ✅ Data Collection Strategy

### 🎯 **Principle: Minimize User Friction, Maximize Security**

```
Admin Pre-fills → Auto-Generate Username → User Sets Password → System Auto-Captures
    (Org Data)        (FirstLast)            (Security)           (Device/IP)
```

**Key Changes (Latest):**
- ✅ **Usernames auto-generated** from first and last name (e.g., JohnDoe, JaneSmith)
- ✅ **Name editing removed** - Users must request admin to change name
- ✅ **Bulk import available** - Upload CSV with multiple users at once
- ✅ **Password-only signup** - Users only set their password during registration

---

## 📋 During Signup (User Input)

### **What User SHOULD Provide:**

| Field | Type | Why User Provides |
|-------|------|-------------------|
| **Password** | Password (required) | Security - only user should know |
| **Password Confirmation** | Password (required) | Prevents typos |

**That's it!** Everything else is pre-filled or auto-generated.

### **What's Pre-filled (Read-Only):**

| Field | Source | Can User Edit? |
|-------|--------|----------------|
| **Email** | Invitation | ❌ No |
| **First Name** | Invitation | ❌ No - Request admin to change |
| **Last Name** | Invitation | ❌ No - Request admin to change |
| **Username** | Auto-generated from FirstLast | ❌ No - Generated automatically |

### **Validation Rules:**
- ✅ Password: Min 12 chars, uppercase + lowercase + numbers
- ✅ Password Match: Confirmation must match
- ✅ Username Unique: Auto-handled with number suffix (JohnDoe1, JohnDoe2, etc.)
- ✅ Name Changes: Contact admin after signup

---

## 🚀 Bulk User Import (NEW!)

### **Admin Can Import Multiple Users via CSV:**

1. **Download Template:** Get CSV template with example data
2. **Fill Data:** Add multiple users (email, name, role, org, apps)
3. **Upload File:** System processes all users at once
4. **Auto-Send Invitations:** Each user receives email invitation

### **CSV Template Format:**

```csv
email,first_name,last_name,role,company_name,department_name,branch_name,assigned_apps
john.doe@example.com,John,Doe,REQUESTER,Quick Services LQS,Finance,Head Office,treasury,workflow
jane.smith@example.com,Jane,Smith,APPROVER,Quick Services LQS,Finance,Head Office,treasury,workflow,reports
```

### **Benefits:**
- ⚡ **Fast:** Create 10+ users in seconds
- ✅ **Accurate:** Template prevents errors
- 📧 **Automated:** Invitations sent automatically
- 🔄 **Duplicate Check:** Prevents duplicate emails
- 📊 **Error Report:** Shows which rows failed and why

### **Access:**
`/accounts/bulk-import/` (requires `add_userinvitation` permission)

---

## 🔒 Pre-filled from Invitation (Read-Only)

### **What Admin SHOULD Pre-fill:**

| Field | Source | Editable by User? |
|-------|--------|-------------------|
| **Email** | Invitation | ❌ No - Validated in invitation |
| **Role** | Invitation | ❌ No - Security risk! |
| **Company** | Invitation | ❌ No - Org structure control |
| **Department** | Invitation | ❌ No - Org structure control |
| **Branch** | Invitation | ❌ No - Org structure control |
| **Assigned Apps** | Invitation | ❌ No - Admin controls access |

### **Why Admin Controls These:**
1. **Role**: Security - prevents privilege escalation
2. **Email**: Already validated via invitation token
3. **Org Structure**: Ensures proper company hierarchy
4. **App Access**: Permission control and licensing

---

## 🤖 Auto-Captured (No User Input)

### **What System SHOULD Auto-Capture:**

| Data | Method | Purpose |
|------|--------|---------|
| **Device Name** | User-Agent parsing | Security tracking |
| **User Agent** | HTTP header | Browser/OS detection |
| **IP Address** | Request metadata | Geo-tracking, audit |
| **Location** | IP geolocation (ip-api.com) | Security monitoring |
| **Signup Timestamp** | `timezone.now()` | Audit trail |
| **Invitation Token** | URL parameter | Link signup to invitation |

### **Privacy Notice:**
Display in signup form:
```
⚠️ Security Information
• Your current device will be automatically whitelisted
• Device info: Windows 11 - Chrome Browser
• Your IP address and location will be logged for security
```

---

## ❌ What User Should NOT Provide

### **Never Ask User For:**

1. ❌ **Username**
   - Risk: Duplicate usernames, inappropriate names
   - Solution: Auto-generate from FirstLast name

2. ❌ **Name (First/Last)**
   - Risk: User enters wrong name, typos
   - Solution: Admin sets in invitation, user requests changes via admin

3. ❌ **Role Selection** 
   - Risk: Users could give themselves admin access
   - Solution: Admin assigns via invitation

4. ❌ **Email Address** 
   - Risk: Typos, fake emails
   - Solution: Email validated in invitation

5. ❌ **App Access**
   - Risk: Unauthorized access to restricted apps
   - Solution: Admin grants app permissions

6. ❌ **Device Whitelist**
   - Risk: Manual errors, security bypass
   - Solution: Auto-whitelist during signup

7. ❌ **Location**
   - Risk: Fake location, VPN bypass
   - Solution: Auto-detect from IP address

---

## 📊 Data Flow Diagram (Updated)

```
┌─────────────────────────┐
│  Admin Creates          │
│  Invitation (or Bulk)   │
└────────┬────────────────┘
         │
         │ Sends Email with Token
         ▼
┌─────────────────────────┐
│  User Clicks Invite     │
│  Link                   │
└────────┬────────────────┘
         │
         │ Pre-filled: Email, Name, Role, Org
         │ Auto-generated: Username (FirstLast)
         ▼
┌─────────────────────────┐
│  User Only Provides:    │
│  • Password             │──── Validation: 12+ chars, complexity
│  • Confirm Password     │──── Validation: Must match
└────────┬────────────────┘
         │
         │ Auto-captured: Device, IP, Location
         │ Username: JohnDoe (or JohnDoe1 if duplicate)
         ▼
┌─────────────────────────┐
│  Account Created        │
│  Device Whitelisted     │
│  Audit Logged           │
└─────────────────────────┘
```

**Key Improvement:** User friction reduced from 5 fields → 2 fields (password only!)

---

## 🔐 Username Generation Logic

### **Auto-Generation Rules:**

1. **Base Format:** `FirstnameLastname` (no spaces, CamelCase)
   - Example: John Doe → `JohnDoe`
   - Example: Jane Smith → `JaneSmith`

2. **Duplicate Handling:** Add number suffix
   - First: `JohnDoe`
   - Second: `JohnDoe1`
   - Third: `JohnDoe2`

3. **Special Characters:** Removed from names
   - Mary-Ann → `MaryAnn`
   - O'Connor → `OConnor`

4. **Case Insensitive:** Check prevents `johndoe` and `JohnDoe`

### **Benefits:**
- ✅ **Consistent:** All usernames follow same pattern
- ✅ **Professional:** FirstLast format is corporate standard
- ✅ **No Duplicates:** Auto-numbering prevents conflicts
- ✅ **Easy to Remember:** Based on actual name

---

## 👤 Name Change Request Process

### **If User's Name is Wrong:**

1. **User logs in** with auto-generated username
2. **User contacts admin** (email or support ticket)
3. **Admin updates** first_name and last_name in Django Admin
4. **Username stays same** (FirstLast format preserved)

### **Important:**
- ❌ Users cannot self-edit their name (security)
- ✅ Username doesn't change (based on original invitation)
- ✅ Display name updates everywhere after admin changes it

---

## 🔐 Security vs UX Balance

### **Current Implementation (v2.0):**

| Aspect | Security | User Experience |
|--------|----------|-----------------|
| **Pre-filled Data** | ✅ High - Admin controls | ✅ High - Less typing |
| **Auto Username** | ✅ High - Consistent format | ✅ High - No thinking required |
| **Password Creation** | ✅ High - Complexity rules | ⚠️ Medium - Rules can be strict |
| **Name Locked** | ✅ High - Admin approval required | ✅ High - No confusion |
| **Auto Device Whitelist** | ✅ High - Immediate tracking | ✅ High - No manual setup |
| **Role Assignment** | ✅ High - Admin only | ✅ High - No confusion |
| **Bulk Import** | ✅ High - Faster onboarding | ✅ High - Less admin work |

**Overall Rating: ✅ EXCELLENT - Reduced from 5 fields to 2 fields!**

**Improvements from v1.0:**
- ❌ Removed: Username input (was 1 field)
- ❌ Removed: Name editing (was 2 fields)  
- ✅ Result: **60% less user input** (5 fields → 2 fields)

---

## 🎨 Optional Fields (Future Enhancement)

### **Consider Adding (Post-Signup):**

1. **Profile Photo** 
   - When: After first login
   - Optional: Yes
   - Storage: S3/media folder

2. **Phone Number**
   - When: Profile completion wizard
   - Optional: Yes
   - Use: 2FA, contact info

3. **Preferred Language**
   - When: First login
   - Optional: Yes (default: English)
   - Use: UI localization

4. **Time Zone**
   - When: First login
   - Optional: Yes (auto-detect)
   - Use: Timestamp display

### **Post-Signup Flow:**
```
Signup → Login → Profile Wizard → Optional Fields → Dashboard
         ↓
         Skip Option Available
```

---

## 📱 Mobile vs Desktop Considerations

### **Device Detection:**
- Automatically detect OS and browser
- Show appropriate UI (responsive design)
- Track device type for analytics

### **Mobile-Specific:**
- Larger input fields
- Password show/hide toggle
- Biometric support (future)

---

## 🌍 Privacy & Compliance

### **GDPR Considerations:**

1. **Email Address**: Collected with consent (invitation acceptance)
2. **IP Address**: Legitimate interest (security/fraud prevention)
3. **Location**: Derived from IP, not GPS (less invasive)
4. **Device Info**: Security necessity (access control)

### **User Rights:**
- ✅ View their devices: `/accounts/my-devices/`
- ✅ Request device deletion: Contact admin
- ✅ Export data: Django admin export
- ✅ Account deletion: Admin can delete user

### **Privacy Notice Display:**
Add to signup form:
```html
<small class="text-muted">
  By creating an account, you agree to our collection of email, 
  device info, and IP address for security purposes. 
  See <a href="/privacy-policy">Privacy Policy</a>.
</small>
```

---

## 🧪 Testing Checklist

### **Signup Flow Tests:**

- [ ] Admin creates invitation with all fields
- [ ] User receives email with valid token
- [ ] Email field is pre-filled and disabled
- [ ] First/Last name displayed (read-only)
- [ ] Username auto-generated and shown as preview (FirstLast)
- [ ] Password validation works (length, complexity)
- [ ] Password confirmation matches
- [ ] Device auto-detected and whitelisted
- [ ] IP and location auto-captured
- [ ] User assigned correct role from invitation
- [ ] User assigned correct company/dept/branch
- [ ] User gets access to assigned apps
- [ ] Invitation marked as "accepted"
- [ ] Duplicate username gets number suffix (JohnDoe1)

### **Bulk Import Tests:**

- [ ] CSV template downloads correctly
- [ ] Template has example data and instructions
- [ ] Upload CSV with 5+ users
- [ ] All valid rows create invitations
- [ ] Invalid rows show error messages
- [ ] Duplicate emails rejected
- [ ] Invalid roles rejected
- [ ] Non-existent org entities rejected
- [ ] Each user receives invitation email
- [ ] Usernames auto-generated correctly
- [ ] Success/error counts displayed

### **Name Change Tests:**

- [ ] User cannot edit name during signup
- [ ] Admin can change name in Django Admin
- [ ] Display name updates after admin change
- [ ] Username remains unchanged

### **Edge Cases:**

- [ ] Expired invitation shows error
- [ ] Already used invitation shows error
- [ ] Invalid token shows 404
- [ ] Weak password rejected
- [ ] Duplicate username auto-numbered (JohnDoe → JohnDoe1)
- [ ] Empty required fields in CSV rejected
- [ ] Special characters in names handled (Mary-Ann → MaryAnn)

---

## 📈 Analytics & Metrics

### **Track During Onboarding:**

1. **Signup Completion Rate**
   - Formula: `Signups / Invitations Sent * 100`
   - Goal: >80%

2. **Name Edit Rate**
   - Formula: `Name Edits / Signups * 100`
   - Insight: Admin data accuracy

3. **Password Retry Rate**
   - Formula: `Password Errors / Signups`
   - Insight: Complexity too high?

4. **Time to Complete**
   - Average time from invite click to signup
   - Goal: <3 minutes

---

## 🔄 Workflow Summary

### **Admin's Job (Individual Invite):**
1. ✅ Create invitation
2. ✅ Set email, first name, last name
3. ✅ Set role, company, dept, branch
4. ✅ Assign app access
5. ✅ Send invitation email

### **Admin's Job (Bulk Import):**
1. ✅ Download CSV template
2. ✅ Fill template with user data
3. ✅ Upload CSV file
4. ✅ Review success/error report
5. ✅ System auto-sends invitations

### **User's Job:**
1. ✅ Click invitation link
2. ✅ Create strong password
3. ✅ Confirm password
4. ✅ Submit form

**That's it! Only 3 steps for users!**

### **System's Job:**
1. ✅ Validate password
2. ✅ Auto-generate username (FirstLast)
3. ✅ Handle duplicates (add number suffix)
4. ✅ Detect device and location
5. ✅ Create user account
6. ✅ Whitelist device
7. ✅ Log audit trail
8. ✅ Mark invitation as accepted
9. ✅ Send welcome email (optional)

---

## 🎯 Recommendations

### **Current Setup: ✅ OPTIMAL (v2.0 - IMPROVED)**

Your implementation now follows industry best practices with **major improvements**:
- ✅ Minimal user input (password only - down from 5 fields!)
- ✅ Auto-generated usernames (consistent FirstLast format)
- ✅ Name changes require admin approval (better security)
- ✅ Bulk import for fast onboarding (10+ users at once)
- ✅ Admin controls security-critical fields
- ✅ Auto-capture for security data
- ✅ Strong password requirements
- ✅ Device whitelisting automatic

### **Key Improvements from v1.0:**
1. ✅ **Removed username input** - Auto-generated from name
2. ✅ **Removed name editing** - Admin approval required
3. ✅ **Added bulk import** - CSV upload for multiple users
4. ✅ **Better security** - Less user control over identity
5. ✅ **Faster signup** - 60% less fields (5→2)

### **Optional Future Enhancements:**

1. **Welcome Email Template**
   - After signup, send formatted welcome email
   - Include username reminder: "Your username is JohnDoe"
   - Include login link and help resources

2. **Profile Completion Wizard**
   - Post-login, prompt for optional fields
   - Phone, photo, preferences
   - Allow skip

3. **Password Strength Meter**
   - Visual indicator during typing
   - "Weak" → "Medium" → "Strong"

4. **Admin Dashboard**
   - Bulk import history
   - Success/error statistics
   - Most common import errors

---

## 📚 Related Documentation

- [USER_INVITATION_GUIDE.md](./USER_INVITATION_GUIDE.md) - Full invitation workflow
- [IP_WHITELIST_GUIDE.md](./IP_WHITELIST_GUIDE.md) - IP security setup
- [SECURITY_OVERVIEW.md](./SECURITY_OVERVIEW.md) - Complete security architecture

---

## 🆘 Troubleshooting

### **Issue: Users confused about what to enter**
**Solution:** Clear labels and helper text (already implemented)

### **Issue: Admin data wrong (typos in name)**
**Solution:** Allow name editing during signup (already implemented)

### **Issue: Users forget username**
**Solution:** Add "Username Recovery" via email

### **Issue: Too many password rejections**
**Solution:** Display requirements BEFORE form submission

---

**Last Updated:** 2024
**Maintained By:** Development Team
