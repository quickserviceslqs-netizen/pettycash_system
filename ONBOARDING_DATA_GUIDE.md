# 📝 Onboarding Data Collection Guide

## Overview
This guide explains **what data should be collected during user onboarding**, optimizing for both **security** and **user experience**.

---

## ✅ Data Collection Strategy

### 🎯 **Principle: Minimize User Friction, Maximize Security**

```
Admin Pre-fills → User Creates → System Auto-Captures
    (Org Data)      (Credentials)      (Security)
```

---

## 📋 During Signup (User Input)

### **What User SHOULD Provide:**

| Field | Type | Why User Provides |
|-------|------|-------------------|
| **Username** | Text (required) | Personal choice, unique identity |
| **Password** | Password (required) | Security - only user should know |
| **Password Confirmation** | Password (required) | Prevents typos |
| **First Name** | Text (optional edit) | User can correct admin's entry |
| **Last Name** | Text (optional edit) | User can correct admin's entry |

### **Validation Rules:**
- ✅ Username: Letters, numbers, @/./+/-/_ only
- ✅ Password: Min 12 chars, uppercase + lowercase + numbers
- ✅ Password Match: Confirmation must match
- ✅ Username Unique: Check database

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

1. ❌ **Role Selection** 
   - Risk: Users could give themselves admin access
   - Solution: Admin assigns via invitation

2. ❌ **Email Address** 
   - Risk: Typos, fake emails
   - Solution: Email validated in invitation

3. ❌ **Company/Department/Branch**
   - Risk: Wrong org structure, permissions leakage
   - Solution: Admin assigns organizational hierarchy

4. ❌ **App Access**
   - Risk: Unauthorized access to restricted apps
   - Solution: Admin grants app permissions

5. ❌ **Device Whitelist**
   - Risk: Manual errors, security bypass
   - Solution: Auto-whitelist during signup

6. ❌ **Location**
   - Risk: Fake location, VPN bypass
   - Solution: Auto-detect from IP address

---

## 📊 Data Flow Diagram

```
┌─────────────────┐
│  Admin Creates  │
│   Invitation    │
└────────┬────────┘
         │
         │ Sends Email with Token
         ▼
┌─────────────────┐
│  User Clicks    │
│  Invite Link    │
└────────┬────────┘
         │
         │ Pre-filled: Email, Name, Role, Org
         ▼
┌─────────────────┐
│  User Provides: │
│  • Username     │──── Validation: Unique, valid chars
│  • Password     │──── Validation: 12+ chars, complexity
│  • Edits Name   │──── Optional: Fix admin's typo
└────────┬────────┘
         │
         │ Auto-captured: Device, IP, Location
         ▼
┌─────────────────┐
│  Account Created│
│  Device Whitelisted │
│  Audit Logged   │
└─────────────────┘
```

---

## 🔐 Security vs UX Balance

### **Current Implementation:**

| Aspect | Security | User Experience |
|--------|----------|-----------------|
| **Pre-filled Data** | ✅ High - Admin controls | ✅ High - Less typing |
| **Username Choice** | ⚠️ Medium - Unique check | ✅ High - Personalization |
| **Password Creation** | ✅ High - Complexity rules | ⚠️ Medium - Rules can be strict |
| **Name Editing** | ✅ High - Cosmetic only | ✅ High - Corrects typos |
| **Auto Device Whitelist** | ✅ High - Immediate tracking | ✅ High - No manual setup |
| **Role Assignment** | ✅ High - Admin only | ✅ High - No confusion |

**Overall Rating: ✅ Excellent Balance**

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
- [ ] User can edit first/last name
- [ ] Username validation works (unique, valid chars)
- [ ] Password validation works (length, complexity)
- [ ] Password confirmation matches
- [ ] Device auto-detected and whitelisted
- [ ] IP and location auto-captured
- [ ] User assigned correct role from invitation
- [ ] User assigned correct company/dept/branch
- [ ] User gets access to assigned apps
- [ ] Invitation marked as "accepted"

### **Edge Cases:**

- [ ] Expired invitation shows error
- [ ] Already used invitation shows error
- [ ] Invalid token shows 404
- [ ] Weak password rejected
- [ ] Duplicate username rejected
- [ ] Empty required fields rejected

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

### **Admin's Job:**
1. ✅ Create invitation
2. ✅ Set role, company, dept, branch
3. ✅ Assign app access
4. ✅ Send invitation email

### **User's Job:**
1. ✅ Click invitation link
2. ✅ Choose username
3. ✅ Create strong password
4. ✅ (Optional) Edit name if wrong
5. ✅ Submit form

### **System's Job:**
1. ✅ Validate all inputs
2. ✅ Detect device and location
3. ✅ Create user account
4. ✅ Whitelist device
5. ✅ Log audit trail
6. ✅ Mark invitation as accepted
7. ✅ Send welcome email (optional)

---

## 🎯 Recommendations

### **Current Setup: ✅ OPTIMAL**

Your implementation already follows best practices:
- ✅ Minimal user input (username + password only)
- ✅ Admin controls security-critical fields
- ✅ Auto-capture for security data
- ✅ Good UX with pre-filled fields
- ✅ Strong password requirements
- ✅ Device whitelisting automatic

### **Optional Improvements:**

1. **Add Welcome Email**
   - After signup, send confirmation email
   - Include login link and help resources

2. **Profile Completion Wizard**
   - Post-login, prompt for optional fields
   - Phone, photo, preferences
   - Allow skip

3. **Password Strength Meter**
   - Visual indicator during typing
   - "Weak" → "Medium" → "Strong"

4. **Username Suggestions**
   - If chosen username taken
   - Suggest: `username1`, `username_2024`, etc.

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
