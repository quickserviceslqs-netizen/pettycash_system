# 📧 User Invitation & Device Whitelisting Guide

## Overview

The system now features a secure **email-based invitation signup process** with **automatic device whitelisting**. This ensures that:
- Only invited users can join the system
- Users can only register from approved devices/locations
- All devices are automatically tracked and logged
- Admins have full visibility and control over registered devices

---

## 🔄 How It Works

### Invitation Flow

```
Admin Sends Invitation → Email with Token Link → User Clicks Link → 
User Completes Signup → Device Auto-Whitelisted → Account Created → User Logged In
```

### Security Features

1. **Email Verification**: Only users with valid invitation can register
2. **Token-Based**: Unique, secure UUID tokens prevent unauthorized access
3. **Expiration**: Invitations expire after configurable days (default: 7)
4. **Device Fingerprinting**: Captures OS, browser, IP, location during signup
5. **Auto-Whitelisting**: First device is automatically whitelisted and set as primary
6. **Activity Logging**: All registration events logged with full context

---

## 📋 Features

### For Administrators

**Send Invitations**
- Navigate to: `/accounts/invite/`
- Fill in user details (email, name, role)
- Assign organization (company, department, branch)
- Select apps to assign
- System sends email with signup link

**Manage Invitations**
- View all invitations: `/accounts/invitations/`
- See status: Pending, Accepted, Expired, Revoked
- Resend invitations
- Revoke pending invitations
- Track who invited whom

**Manage User Devices**
- View user's registered devices: `/accounts/users/<user_id>/devices/`
- See device details: IP, location, last used
- View access attempt history
- Monitor security events

### For Users

**Complete Registration**
- Click invitation link from email
- Choose username and password
- Password must meet security requirements:
  - Minimum length (default: 12 characters)
  - Complexity: uppercase, lowercase, numbers
- Device automatically registered
- Immediate login after signup

**Manage My Devices**
- View whitelisted devices: `/accounts/my-devices/`
- See device info: name, IP, location, last used
- Deactivate non-primary devices
- Set different device as primary

---

## ⚙️ Configuration

### Settings Manager

| Setting | Category | Type | Default | Description |
|---------|----------|------|---------|-------------|
| **INVITATION_EXPIRY_DAYS** | Security | Integer | `7` | Days before invitation link expires |
| **MIN_PASSWORD_LENGTH** | Security | Integer | `12` | Minimum password characters |
| **REQUIRE_PASSWORD_COMPLEXITY** | Security | Boolean | `true` | Require uppercase, lowercase, numbers |
| **ENABLE_ACTIVITY_GEOLOCATION** | Security | Boolean | `true` | Track location during signup |
| **ENABLE_IP_WHITELIST** | Security | Boolean | `false` | Restrict access to whitelisted IPs |

### Django Settings (settings.py)

```python
# Site information for email invitations
SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000')
SITE_NAME = os.environ.get('SITE_NAME', 'Petty Cash System')

# Email configuration (required for invitations)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # or your SMTP server
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@company.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'Petty Cash System <noreply@company.com>'
```

---

## 📧 Email Configuration

### Gmail Setup (Development/Testing)

1. **Enable 2FA** on your Gmail account
2. **Generate App Password**:
   - Go to: https://myaccount.google.com/apppasswords
   - Select app: Mail
   - Select device: Other (Custom name)
   - Copy generated 16-character password
3. **Update settings.py** or environment variables:

```python
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'xxxx xxxx xxxx xxxx'  # App password
```

### Production Email (Render/Railway)

**Environment Variables:**
```bash
EMAIL_HOST=smtp.sendgrid.net  # or mailgun, AWS SES
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-api-key
DEFAULT_FROM_EMAIL=Petty Cash System <noreply@yourcompany.com>
SITE_URL=https://your-app.onrender.com
```

**Recommended Services:**
- **SendGrid**: 100 emails/day free
- **Mailgun**: 5,000 emails/month free
- **AWS SES**: $0.10 per 1,000 emails
- **Mailjet**: 200 emails/day free

---

## 🚀 Usage Guide

### Step 1: Send Invitation

**Admin Action:**
1. Login as admin
2. Navigate to: **Users → Send Invitation**
3. Fill in form:
   - Email: `newuser@company.com`
   - First Name: `John`
   - Last Name: `Doe`
   - Role: `staff`
   - Company: Select from dropdown
   - Department: Select from dropdown
   - Apps: Check boxes for apps to assign
4. Click **Send Invitation**

**What Happens:**
- Invitation created in database
- Unique token generated
- Email sent to user with signup link
- Invitation status: `Pending`
- Expiration set to 7 days from now

### Step 2: User Receives Email

**Email Content:**
```
Subject: You've been invited to join Petty Cash System

Hello John,

You've been invited to join our Petty Cash Management System as a Staff.

[Complete Your Registration Button]

This invitation will expire on December 1, 2025 at 3:30 PM.

Security Notes:
- Your device will be automatically registered when you complete signup
- You can only sign up from approved locations (if IP whitelist is enabled)
- Make sure to use a strong password
```

### Step 3: User Clicks Link

**What Happens:**
- User taken to: `/accounts/signup/<unique-token>/`
- System validates token
- Checks if invitation is still valid (not expired, not revoked)
- Shows signup form pre-filled with email

### Step 4: User Completes Signup

**User Actions:**
1. Choose username
2. Create password (must meet requirements)
3. Confirm password
4. View security notice about device whitelisting
5. Click **Create Account & Whitelist Device**

**What Happens:**
- User account created with:
  - Username, email, password
  - Role from invitation
  - Company, department, branch from invitation
  - Assigned apps from invitation
- Device information captured:
  - OS detected (Windows 10/11, macOS, Linux, Android, iOS)
  - Browser detected (Chrome, Edge, Firefox, Safari)
  - IP address extracted
  - Location fetched from IP geolocation API
- WhitelistedDevice record created:
  - Device name: "Windows 10/11 - Chrome"
  - IP address: "197.248.10.50"
  - Location: "Nairobi, Nairobi County, Kenya"
  - Is Primary: `True`
  - Registration method: `signup`
- Invitation status updated: `Accepted`
- Activity logged with full details
- User automatically logged in
- Redirected to dashboard

### Step 5: Manage Devices

**User Can:**
- View all whitelisted devices
- See device details (IP, location, last used)
- Deactivate non-primary devices
- Set different device as primary

**Admin Can:**
- View all users' devices
- See access attempt history
- Monitor blocked access attempts
- Manually activate/deactivate devices

---

## 🔒 Security Implementation

### Device Whitelisting

**WhitelistedDevice Model:**
```python
- user: ForeignKey to User
- device_name: "Windows 10/11 - Chrome"
- user_agent: Full user agent string
- ip_address: GenericIPAddressField
- location: "City, Region, Country"
- is_active: Boolean
- is_primary: Boolean (cannot be deactivated)
- registration_method: signup | manual | self_service
- registered_at: DateTime
- last_used_at: DateTime (auto-updated)
```

**Device Detection:**
```python
def get_device_info(request):
    # Parses user agent to extract:
    - OS: Windows 10/11, macOS, Linux, Android, iOS
    - Browser: Chrome, Edge, Firefox, Safari
    
    Returns: {
        'device_name': "Windows 10/11 - Chrome",
        'user_agent': "Mozilla/5.0..."
    }
```

**Location Tracking:**
```python
def get_location(ip_address):
    # Calls ip-api.com geolocation API
    # Returns: "Nairobi, Nairobi County, Kenya"
    # Respects ENABLE_ACTIVITY_GEOLOCATION setting
```

### Access Logging

**DeviceAccessAttempt Model:**
```python
- user: ForeignKey (null if unauthenticated)
- ip_address: GenericIPAddressField
- device_name: CharField
- user_agent: TextField
- location: CharField
- was_allowed: Boolean
- reason: "Device not whitelisted" | "IP not in whitelist"
- attempted_at: DateTime
- request_path: URL path attempted
```

**When Logged:**
- Every successful login
- Every blocked access attempt
- Unusual location access
- Multiple concurrent sessions
- IP whitelist violations

### Invitation Security

**UserInvitation Model:**
```python
- email: EmailField (unique per pending invitation)
- token: UUIDField (unique, auto-generated)
- status: pending | accepted | expired | revoked
- expires_at: DateTime (created_at + INVITATION_EXPIRY_DAYS)
- invited_by: ForeignKey to admin User
- user: ForeignKey to created User (null until accepted)
```

**Validation:**
```python
def is_valid(self):
    # Checks:
    - Status == 'pending'
    - Current time < expires_at
    - Auto-updates to 'expired' if expired
```

---

## 📊 Admin Dashboard Integration

### Invitations Management

**List View: `/accounts/invitations/`**
- Stats cards: Pending, Accepted, Expired
- Table with all invitations
- Actions: Resend, Revoke
- Link to user devices (if accepted)

**Send Invitation: `/accounts/invite/`**
- Form with all fields
- Organization dropdowns
- App checkboxes
- Security notes displayed

### User Device Management

**User Devices View: `/accounts/users/<id>/devices/`**
- Breadcrumb navigation
- Whitelisted devices table
- Recent access attempts (last 20)
- Color-coded: blocked attempts in red

**User's Own Devices: `/accounts/my-devices/`**
- Cards for each device
- Primary device highlighted
- Actions: Set Primary, Deactivate
- Cannot deactivate primary device

---

## 🧪 Testing Guide

### Test 1: Full Invitation Flow

1. **Send Invitation:**
   ```
   Email: test@example.com
   Role: staff
   Apps: Transactions
   ```

2. **Check Email:**
   - Verify invitation email received
   - Click signup link
   - Verify link format: `/accounts/signup/<uuid>/`

3. **Complete Signup:**
   - Username: `testuser`
   - Password: `SecurePass123`
   - Verify device info displayed: "Windows 10/11 - Chrome"

4. **Verify Creation:**
   - User account created
   - Device whitelisted
   - User logged in automatically
   - Check `/accounts/my-devices/` shows device

5. **Admin Verification:**
   - Check `/accounts/invitations/` shows "Accepted"
   - Check `/accounts/users/<id>/devices/` shows device

### Test 2: Expired Invitation

1. Send invitation
2. Change `expires_at` to past date in database
3. Click link
4. Verify error page: "Invitation Expired"

### Test 3: Device Management

1. Complete signup (device auto-registered as primary)
2. Go to `/accounts/my-devices/`
3. Verify device shown as "Primary"
4. Try to deactivate primary device
5. Verify error: "Cannot deactivate primary device"

### Test 4: Multiple Devices (Manual Test)

1. Complete signup on Chrome
2. Login from Firefox on same computer
3. Admin adds second device manually
4. User can now set Firefox as primary
5. User can deactivate Chrome device

---

## 🔧 Troubleshooting

### Issue 1: Emails Not Sending

**Symptoms:**
- Invitation sent but no email received
- Error: "SMTPAuthenticationError"

**Solutions:**
1. Check email settings in Django settings
2. Verify EMAIL_HOST_PASSWORD is correct
3. For Gmail: use App Password, not regular password
4. Check spam folder
5. Test email configuration:
```python
python manage.py shell
from django.core.mail import send_mail
send_mail('Test', 'Message', 'from@example.com', ['to@example.com'])
```

### Issue 2: Invitation Link Returns 404

**Symptoms:**
- User clicks link, gets 404 page

**Causes:**
- Token doesn't match database
- Invitation already accepted/expired
- URL malformed in email

**Solutions:**
1. Check invitation exists: `UserInvitation.objects.filter(token=<uuid>)`
2. Check status: Should be 'pending'
3. Verify URL pattern in urls.py

### Issue 3: Device Not Auto-Registered

**Symptoms:**
- User completes signup but no device in database

**Causes:**
- Error during device creation
- Geolocation API failed

**Solutions:**
1. Check logs for errors
2. Set `ENABLE_ACTIVITY_GEOLOCATION` to `false` if API failing
3. Manually create device in admin

### Issue 4: Cannot Access After Signup

**Symptoms:**
- User completes signup but cannot login

**Causes:**
- IP whitelist enabled but user IP not whitelisted
- Device whitelist middleware blocking

**Solutions:**
1. Temporarily disable IP whitelist
2. Add user's IP to whitelist
3. Check middleware settings

---

## 📈 Use Cases

### Use Case 1: New Employee Onboarding

**Scenario:**
- HR onboards new finance assistant
- Needs access to Transactions and Reports apps

**Process:**
1. Admin sends invitation with:
   - Role: `staff`
   - Apps: Transactions, Reports
   - Department: Finance
2. Employee receives email
3. Completes signup from office computer
4. Device whitelisted: "Windows 10/11 - Chrome"
5. Location logged: "Nairobi, Kenya"
6. Employee can immediately access assigned apps

**Security Benefits:**
- Only invited employees can join
- Device fingerprinted and tracked
- Location logged for audit
- No manual device whitelisting needed

### Use Case 2: Remote Worker

**Scenario:**
- Accountant works from home
- Company has IP whitelist enabled

**Process:**
1. Admin sends invitation
2. Admin adds accountant's home IP to whitelist: `197.248.10.50`
3. Accountant clicks link from home
4. Completes signup (IP validated against whitelist)
5. Device whitelisted
6. Can access system from home

**Security Benefits:**
- IP whitelist prevents signup from unauthorized locations
- Device tracked even for remote workers
- Admin can monitor access from home IP

### Use Case 3: Temporary Contractor

**Scenario:**
- External auditor needs temporary access
- Only for 30 days

**Process:**
1. Admin sends invitation with role: `fp&a`
2. Contractor registers, device whitelisted
3. After 30 days, admin:
   - Deactivates user account
   - OR deactivates whitelisted device
4. Contractor cannot access system anymore

**Security Benefits:**
- Controlled access period
- Full audit trail of contractor access
- Easy deactivation without deleting account

### Use Case 4: Multi-Device User

**Scenario:**
- CFO uses office PC and personal laptop

**Process:**
1. CFO completes signup on office PC (primary device)
2. CFO tries to access from laptop at home
3. Admin receives alert: "Unusual location/device"
4. Admin reviews access attempt
5. Admin manually whitelists laptop device
6. CFO can now use both devices

**Security Benefits:**
- Primary device always whitelisted
- Additional devices require approval
- Alerts on new device attempts
- Full visibility of all user devices

---

## 🎯 Best Practices

### For Administrators

1. **Send Invitations Promptly**
   - Don't wait until employee's first day
   - Send 2-3 days before start date
   - Gives time for setup and issues

2. **Verify Email Addresses**
   - Double-check email before sending
   - Use company email addresses only
   - Avoid personal emails for security

3. **Monitor Pending Invitations**
   - Check `/accounts/invitations/` weekly
   - Resend if not accepted within 3 days
   - Revoke expired/unused invitations

4. **Review Device Access**
   - Weekly review of access attempts
   - Investigate blocked attempts
   - Deactivate unused devices

5. **Set Appropriate Expiry**
   - Default 7 days works for most cases
   - Shorter (3 days) for urgent roles
   - Longer (14 days) for remote contractors

### For Users

1. **Complete Signup Promptly**
   - Register within 48 hours of receiving invitation
   - Contact admin if link expired

2. **Use Strong Passwords**
   - Follow complexity requirements
   - Don't reuse passwords from other sites
   - Use password manager

3. **Register Primary Device First**
   - Use your main work device for signup
   - This becomes your primary device

4. **Request Additional Devices**
   - Contact admin before using new device
   - Explain why additional device needed

5. **Keep Devices Updated**
   - Review devices monthly
   - Deactivate old/unused devices

---

## 📝 Summary

**User Invitation & Device Whitelisting System:**
- ✅ Secure email-based invitation workflow
- ✅ Token-based signup links with expiration
- ✅ Automatic device fingerprinting and whitelisting
- ✅ IP address and location tracking
- ✅ Complete activity audit trail
- ✅ Admin control over invitations and devices
- ✅ User self-service device management
- ✅ Integration with IP whitelist security
- ✅ Comprehensive access attempt logging

**Benefits:**
- **Security**: Only invited users can join
- **Compliance**: Full audit trail of all registrations
- **Convenience**: Automatic device whitelisting
- **Visibility**: Admins see all devices and access attempts
- **Control**: Easy device activation/deactivation
- **Scalability**: Handles remote workers and multiple devices

**Requirements:**
- Email configuration (SMTP)
- Site URL set in settings
- Settings Manager configured
- IP geolocation API (optional)

The system is now production-ready for secure user onboarding! 🎉
