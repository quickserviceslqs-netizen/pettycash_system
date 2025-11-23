# 🌐 IP Address Whitelist Security Guide

## Overview

The IP Address Whitelist feature restricts system access to only approved IP addresses or network ranges. This is a critical security layer for organizations that want to limit access to specific locations (offices, VPN networks, etc.).

---

## 📋 How It Works

### 1. **Request Flow**
```
User Request → IP Whitelist Middleware → Check Enabled → Extract IP → Validate → Allow/Block
```

### 2. **Enforcement Points**
- **Middleware Layer**: Checks every HTTP request before it reaches your application
- **After Authentication**: Runs after session middleware but before view processing
- **Logging**: All blocked attempts are logged in Activity Log

### 3. **IP Extraction**
The system extracts the client IP using this priority:
1. `HTTP_X_FORWARDED_FOR` header (for proxy/load balancer setups)
2. `REMOTE_ADDR` (direct connection)

**Example in Production (Render/Railway):**
- Request from `197.248.10.50` → Proxy (Render) → App
- App sees: `HTTP_X_FORWARDED_FOR: 197.248.10.50, 10.0.0.1`
- Middleware extracts: `197.248.10.50` (actual client IP)

---

## ⚙️ Configuration Settings

### Security Settings in Settings Manager

| Setting | Type | Description | Default |
|---------|------|-------------|---------|
| **ENABLE_IP_WHITELIST** | Boolean | Turn IP filtering on/off | `false` |
| **ALLOWED_IP_ADDRESSES** | Text | Comma-separated list of allowed IPs/ranges | (empty) |

---

## 🔧 Configuration Examples

### Example 1: Single Office IP
**Scenario**: Company has fixed IP at office

```
ENABLE_IP_WHITELIST: true
ALLOWED_IP_ADDRESSES: 197.248.10.50
```

**Result**: Only requests from `197.248.10.50` can access the system

---

### Example 2: Multiple Offices
**Scenario**: Nairobi HQ + Mombasa branch + VPN server

```
ENABLE_IP_WHITELIST: true
ALLOWED_IP_ADDRESSES: 197.248.10.50, 41.90.45.100, 154.72.163.20
```

**Result**: Three specific IPs are allowed

---

### Example 3: Entire Office Network (CIDR)
**Scenario**: Office has network range `192.168.1.0/24` (256 IPs)

```
ENABLE_IP_WHITELIST: true
ALLOWED_IP_ADDRESSES: 192.168.1.0/24
```

**Result**: Anyone on network from `192.168.1.1` to `192.168.1.254` can access

---

### Example 4: Mixed Configuration
**Scenario**: Office network + Home admin + VPN + Mobile IT staff

```
ENABLE_IP_WHITELIST: true
ALLOWED_IP_ADDRESSES: 192.168.1.0/24, 197.248.10.50, 10.8.0.0/16, 41.90.45.100
```

**Breakdown**:
- `192.168.1.0/24` - Office LAN (192.168.1.1-254)
- `197.248.10.50` - Home admin IP
- `10.8.0.0/16` - VPN network (10.8.0.1 - 10.8.255.254)
- `41.90.45.100` - Mobile IT staff

---

## 📊 CIDR Notation Reference

| Notation | IP Range | Total IPs | Use Case |
|----------|----------|-----------|----------|
| `192.168.1.100` | Single IP | 1 | Specific device |
| `192.168.1.0/32` | Single IP | 1 | Same as above |
| `192.168.1.0/30` | .0 - .3 | 4 | Very small subnet |
| `192.168.1.0/28` | .0 - .15 | 16 | Small office |
| `192.168.1.0/24` | .0 - .255 | 256 | Medium office |
| `192.168.0.0/22` | .0.0 - .3.255 | 1,024 | Large office |
| `10.0.0.0/16` | 10.0.0.0 - 10.0.255.255 | 65,536 | Large network |
| `10.0.0.0/8` | 10.0.0.0 - 10.255.255.255 | 16,777,216 | Entire private range |

**Common Private IP Ranges:**
- `10.0.0.0/8` - Large private networks
- `172.16.0.0/12` - Medium private networks
- `192.168.0.0/16` - Small private networks (most home/office routers)

---

## 🛠️ Implementation Details

### Middleware Classes

#### 1. **IPWhitelistMiddleware**
Located in: `pettycash_system/ip_whitelist_middleware.py`

**What it does**:
- Checks if `ENABLE_IP_WHITELIST` is `true`
- Extracts client IP from request
- Checks if URL is exempt (login page, static files)
- Validates IP against whitelist
- Blocks access if IP not allowed (returns 403 Forbidden)

**Exempt URLs** (always accessible):
- `/accounts/login/` - Login page
- `/admin/login/` - Admin login
- `/static/` - CSS, JavaScript, images
- `/media/` - Uploaded files

**Why exempt?** Users need to see login page and load assets even if blocked.

---

#### 2. **SecurityLoggingMiddleware**
Located in: `pettycash_system/ip_whitelist_middleware.py`

**What it does**:
- Monitors all HTTP responses
- When status code is `403` (Forbidden)
- Logs the blocked attempt to Activity Log
- Records: IP, URL path, timestamp, user (if authenticated)

**Example Log Entry**:
```
Action: system
Description: Blocked access attempt to /dashboard/
Changes: {"ip": "41.90.50.100", "path": "/dashboard/", "reason": "IP not whitelisted"}
Success: False
Error: IP address not in whitelist
IP Address: 41.90.50.100
Location: Nairobi, Kenya
Device: Windows 10/11 - Chrome
```

---

## 🚀 How to Enable

### Step 1: Configure Settings
1. Navigate to: **Settings → Security**
2. Find **IP Whitelist** section
3. Set `ENABLE_IP_WHITELIST` to `true`
4. Add allowed IPs to `ALLOWED_IP_ADDRESSES`

### Step 2: Find Your IP Address
**Method 1** - Online Service:
- Visit: https://whatismyipaddress.com/
- Copy your public IP

**Method 2** - Command Line:
```powershell
# Windows PowerShell
Invoke-RestMethod -Uri "https://api.ipify.org?format=json"
```

**Method 3** - Python (in Django shell):
```python
import requests
response = requests.get('https://api.ipify.org?format=json')
print(response.json()['ip'])
```

### Step 3: Add Your IP to Whitelist
```
Example: 197.248.10.50
```

### Step 4: Test
1. Save settings
2. Open new incognito window
3. Try accessing system
4. Should work if your IP matches

### Step 5: Test Blocking (Optional)
1. Temporarily change `ALLOWED_IP_ADDRESSES` to `192.168.1.100` (fake IP)
2. Try accessing system
3. Should see "Access Denied" message
4. Revert to correct IP

---

## 🔒 Security Best Practices

### 1. **Start with Monitoring**
- Enable IP whitelist with broad range first
- Monitor Activity Logs for blocked attempts
- Identify legitimate IPs
- Narrow down whitelist over time

### 2. **Always Include Admin Access**
- Add your company's static IP
- Include IT admin home IPs (if remote work)
- Include VPN network range

### 3. **Dynamic IP Considerations**
If your ISP uses **dynamic IPs** (changes periodically):
- ❌ **Don't** use IP whitelist (you'll lock yourself out)
- ✅ **Use** VPN with static IP instead
- ✅ **Use** other security measures (2FA, strong passwords)

### 4. **Mobile Users**
Mobile networks use **dynamic IPs** that change frequently:
- ❌ **Don't** add individual mobile IPs
- ✅ **Use** company VPN for mobile access
- ✅ **Use** office WiFi when possible

### 5. **Emergency Access**
**What if you lock yourself out?**

**Option 1** - Disable via Django Shell (server access):
```python
from settings_manager.models import SystemSetting
setting = SystemSetting.objects.get(key='ENABLE_IP_WHITELIST')
setting.value = 'false'
setting.save()
```

**Option 2** - Disable in Code (emergency):
Edit `pettycash_system/settings.py`:
```python
# Temporary override - remove after fixing whitelist
IP_WHITELIST_OVERRIDE_DISABLE = True
```

Then update middleware to check this flag.

**Option 3** - Database Direct:
```sql
UPDATE settings_manager_systemsetting 
SET value = 'false' 
WHERE key = 'ENABLE_IP_WHITELIST';
```

---

## 📊 Monitoring & Troubleshooting

### View Blocked Attempts
1. Navigate to: **Settings → Activity Logs**
2. Filter by:
   - Action: `system`
   - Success: `No`
   - Description contains: `Blocked access attempt`

### Common Issues

#### Issue 1: "I'm blocked even though my IP is whitelisted"
**Causes**:
- IP format error in settings (extra spaces, typo)
- Public IP vs Private IP confusion
- Behind proxy/NAT - actual IP is different

**Solution**:
1. Check Activity Log to see what IP was detected
2. Verify that IP matches whitelist exactly
3. Ensure CIDR notation is correct (e.g., `/24` not `/24.0`)

---

#### Issue 2: "VPN users can't access"
**Causes**:
- VPN assigns different IP range
- VPN uses dynamic IP pool

**Solution**:
1. Find VPN IP range from IT department
2. Add entire VPN subnet (e.g., `10.8.0.0/16`)
3. Test with VPN user

---

#### Issue 3: "Home users can't access"
**Causes**:
- ISP uses dynamic IP (changes daily/weekly)

**Solution**:
- Option 1: Get static IP from ISP (business plan)
- Option 2: Use company VPN with static exit IP
- Option 3: Disable IP whitelist, use other security (2FA)

---

## 🔄 Integration with Other Security Features

### Combined Security Layers
IP Whitelist works with:

1. **Two-Factor Authentication (2FA)**
   - IP whitelist = "Right location"
   - 2FA = "Right person"
   - Together = Maximum security

2. **Location Monitoring**
   - IP whitelist = Prevention
   - Location logs = Detection
   - Alert when blocked attempts from unusual locations

3. **Session Security**
   - IP whitelist = Network access control
   - Session timeout = Time-based control
   - Account lockout = Brute force protection

### Example: Bank-Grade Security
```
Security Settings:
✓ ENABLE_IP_WHITELIST: true
✓ ALLOWED_IP_ADDRESSES: 192.168.1.0/24, 10.8.0.0/16
✓ ENABLE_TWO_FACTOR_AUTH: true
✓ REQUIRE_2FA_FOR_APPROVERS: true
✓ MAX_LOGIN_ATTEMPTS: 3
✓ ACCOUNT_LOCKOUT_DURATION_MINUTES: 30
✓ SESSION_TIMEOUT_MINUTES: 15
✓ ALERT_UNUSUAL_LOCATION: true
```

**Result**: Multi-layered defense-in-depth security

---

## 📈 Use Case Examples

### Use Case 1: Government Agency
**Requirements**:
- Access only from government network
- No external access allowed
- Strict audit trail

**Configuration**:
```
ENABLE_IP_WHITELIST: true
ALLOWED_IP_ADDRESSES: 196.201.214.0/24
ACTIVITY_LOG_RETENTION_DAYS: 2555  # 7 years
ENABLE_AUDIT_TRAIL_ENCRYPTION: true
```

---

### Use Case 2: Remote Company with VPN
**Requirements**:
- Office network + VPN access
- IT admin home access
- No public access

**Configuration**:
```
ENABLE_IP_WHITELIST: true
ALLOWED_IP_ADDRESSES: 192.168.1.0/24, 10.8.0.0/16, 197.248.10.50
```
Where:
- `192.168.1.0/24` - Office LAN
- `10.8.0.0/16` - VPN network
- `197.248.10.50` - IT admin home

---

### Use Case 3: Multi-Branch Organization
**Requirements**:
- 5 branch offices
- Each has static IP
- HQ has larger network

**Configuration**:
```
ENABLE_IP_WHITELIST: true
ALLOWED_IP_ADDRESSES: 192.168.1.0/24, 197.248.10.50, 41.90.45.100, 154.72.163.20, 105.160.50.75, 196.201.214.80
```

---

### Use Case 4: Cloud-First Organization
**Requirements**:
- Staff work from anywhere (dynamic IPs)
- Need security without IP restrictions
- Mobile app access

**Configuration**:
```
ENABLE_IP_WHITELIST: false  # Can't use with dynamic IPs
ENABLE_TWO_FACTOR_AUTH: true  # Use 2FA instead
REQUIRE_2FA_FOR_APPROVERS: true
ALERT_UNUSUAL_LOCATION: true  # Monitor for suspicious logins
MAX_LOGIN_ATTEMPTS: 5
```

---

## 🧪 Testing Guide

### Test 1: Basic Functionality
1. Enable IP whitelist
2. Add your current IP
3. Access system - should work
4. Change IP to fake value
5. Access system - should be blocked

### Test 2: CIDR Range
1. Find your IP (e.g., `192.168.1.50`)
2. Add network range: `192.168.1.0/24`
3. Access should work (your IP is in range)

### Test 3: Multiple IPs
1. Add multiple IPs separated by commas
2. Test from each location
3. Verify all allowed IPs work

### Test 4: Logging
1. Intentionally use blocked IP
2. Check Activity Logs
3. Verify blocked attempt is logged with correct IP

### Test 5: Exempt URLs
1. Enable IP whitelist with wrong IP
2. Visit `/accounts/login/` - should load
3. Visit `/static/styles.css` - should load
4. Visit `/dashboard/` - should be blocked

---

## 📝 Summary

**IP Address Whitelist**:
- ✅ Restricts access to approved IPs/networks
- ✅ Supports individual IPs and CIDR ranges
- ✅ Logs all blocked attempts
- ✅ Exempts login and static files
- ✅ Works with proxy/load balancer setups
- ✅ Integrates with other security features

**When to Use**:
- ✅ Fixed office locations
- ✅ VPN-based access
- ✅ Government/high-security requirements
- ✅ Compliance mandates (network segregation)

**When NOT to Use**:
- ❌ Dynamic ISP IPs (home users without VPN)
- ❌ Mobile-first organizations
- ❌ Global remote workforce without VPN
- ❌ Public-facing applications

**Recommendation**:
Combine IP whitelist with 2FA and location monitoring for maximum security while maintaining usability.
