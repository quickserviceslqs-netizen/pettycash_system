# TREASURY APP - WORKFLOW & FEATURE VARIATIONS

## Overview
The Treasury app handles payment execution, fund management, and treasury operations with role-based feature access.

---

## USER ACCESS LEVELS

### 1. SUPERUSER (Technical Admin)
**Access**: Bypass ALL restrictions
- ✅ Full access to all features
- ✅ Can do everything without explicit permissions
- ✅ Access via Django Admin + Treasury App
- **Use Case**: System administrators, developers

### 2. ADMIN (Business Admin)
**Required**: 
- App Assignment: `treasury` 
- Role: `admin`
- Permissions: Depends on what they need to do

**Features**:
- ✅ View all treasury funds
- ✅ View all payments
- ✅ Manually replenish funds (if role=treasury or admin)
- ✅ View/manage variances
- ✅ View reports and dashboards
- ✅ Manage alerts

### 3. TREASURY STAFF
**Required**:
- App Assignment: `treasury`
- Role: `treasury`
- Permissions: `view_payment`, `add_payment`, `change_payment`, `view_treasuryfund`, etc.

**Features**:
- ✅ Execute payments
- ✅ Send/verify OTP
- ✅ Manually replenish funds
- ✅ View treasury dashboard
- ✅ Track payment status
- ✅ View fund balances
- ✅ Acknowledge alerts
- ❌ Approve variances (CFO only)

### 4. CFO (Chief Financial Officer)
**Required**:
- App Assignment: `treasury`
- Role: `cfo`
- Group: Must be in a group with "cfo" in name
- Permissions: Same as treasury + special approvals

**Features**:
- ✅ All treasury staff features
- ✅ **Approve variance adjustments** (special permission)
- ✅ View financial reports
- ✅ View all alerts

### 5. REGULAR USER (No Treasury Access)
**Access**: NONE
- ❌ Cannot access treasury app
- ❌ Blocked by `RequireAppAccess` permission
- **Use Case**: Requesters who only submit requisitions

---

## TREASURY APP FEATURES

### API ENDPOINTS (All require `treasury` app assignment)

#### 1. **Treasury Funds** (`/treasury/api/funds/`)
**ViewSet**: `TreasuryFundViewSet` (Read-Only)
**Permissions**: 
- Must have `treasury` app assigned
- Must have `treasury.view_treasuryfund` permission

**Endpoints**:
- `GET /funds/` - List all funds
- `GET /funds/{fund_id}/` - Get fund details
- `GET /funds/{fund_id}/balance/` - Get current balance
- `POST /funds/{fund_id}/replenish/` - **Replenish fund** (treasury/admin role ONLY)

**Role Restrictions**:
- Replenish: Only `role=treasury` or `role=admin`

---

#### 2. **Payments** (`/treasury/api/payments/`)
**ViewSet**: `PaymentViewSet` (Full CRUD)
**Permissions**:
- Must have `treasury` app assigned
- CRUD permissions: `view_payment`, `add_payment`, `change_payment`, `delete_payment`

**Endpoints**:
- `GET /payments/` - List payments
- `GET /payments/{payment_id}/` - Get payment details
- `POST /payments/{payment_id}/execute/` - **Execute payment** (deducts from fund)
- `POST /payments/{payment_id}/send-otp/` - Send OTP
- `POST /payments/{payment_id}/verify-otp/` - Verify OTP
- `POST /payments/{payment_id}/retry/` - Retry failed payment

**Workflow**:
1. Requisition approved → Payment created
2. Treasury staff selects fund and executes payment
3. If OTP required → Send OTP → Verify OTP
4. Payment processes → Fund balance deducted
5. Ledger entry created

---

#### 3. **Variance Adjustments** (`/treasury/api/variances/`)
**ViewSet**: `VarianceAdjustmentViewSet` (Read-Only)
**Permissions**: 
- Must have `treasury` app assigned
- Must have `treasury.view_varianceadjustment`

**Endpoints**:
- `GET /variances/` - List all variances
- `GET /variances/{variance_id}/` - Get variance details
- `POST /variances/{variance_id}/approve/` - **Approve variance** (CFO ONLY)

**Role Restrictions**:
- Approve: Must be in group containing "cfo"

---

#### 4. **Replenishment Requests** (`/treasury/api/replenishments/`)
**ViewSet**: `ReplenishmentRequestViewSet` (Read-Only)
**Endpoints**:
- `GET /replenishments/` - List replenishment requests
- `GET /replenishments/{request_id}/` - Get request details

---

#### 5. **Ledger Entries** (`/treasury/api/ledger/`)
**ViewSet**: `LedgerEntryViewSet` (Read-Only)
**Endpoints**:
- `GET /ledger/` - List all ledger entries
- `GET /ledger/{entry_id}/` - Get entry details
- `GET /ledger/by_fund/` - Filter by fund

---

#### 6. **Dashboard** (`/treasury/api/dashboard/`)
**ViewSet**: `DashboardViewSet` (Read-Only)
**Endpoints**:
- `GET /dashboard/` - Get treasury dashboard data
- `GET /dashboard/summary/` - Get summary metrics

---

#### 7. **Alerts** (`/treasury/api/alerts/`)
**ViewSet**: `AlertsViewSet` (Full CRUD)
**Endpoints**:
- `GET /alerts/` - List alerts
- `GET /alerts/unresolved/` - Get unresolved alerts only
- `POST /alerts/{alert_id}/acknowledge/` - Acknowledge alert
- `POST /alerts/{alert_id}/resolve/` - Resolve alert

---

#### 8. **Payment Tracking** (`/treasury/api/tracking/`)
**ViewSet**: `PaymentTrackingViewSet` (Read-Only)
**Endpoints**:
- `GET /tracking/` - Track payment status
- `GET /tracking/{tracking_id}/` - Get tracking details

---

#### 9. **Reports** (`/treasury/api/reports/`)
**ViewSet**: `ReportingViewSet`
**Endpoints**:
- `GET /reports/payment-summary/` - Payment summary report
- `GET /reports/fund-utilization/` - Fund utilization report
- `GET /reports/variance-report/` - Variance report
- `GET /reports/forecast/` - Replenishment forecast
- `POST /reports/export/` - Export report to CSV/PDF

---

## HTML VIEWS (Frontend Pages)

All require `treasury` app assignment:

1. `/treasury/` → Redirects to dashboard
2. `/treasury/dashboard/` → Treasury dashboard view
3. `/treasury/payment-execute/` → Payment execution interface
4. `/treasury/funds/` → Fund management view
5. `/treasury/alerts/` → Alerts management
6. `/treasury/variances/` → Variance adjustments view

---

## PERMISSION VARIATIONS BY ROLE

### SuperUser
```
✅ Everything (bypasses all checks)
```

### Admin (role=admin)
```
✅ View funds
✅ Replenish funds
✅ View payments
✅ View variances
✅ View reports
❌ Approve variances (unless in CFO group)
```

### Treasury Staff (role=treasury)
```
✅ View funds
✅ Replenish funds
✅ Execute payments
✅ Send/verify OTP
✅ View payments
✅ Track payments
✅ Acknowledge alerts
❌ Approve variances
```

### CFO (role=cfo + in CFO group)
```
✅ All Treasury Staff features
✅ Approve variance adjustments
✅ View all financial reports
```

### Regular User (no treasury app)
```
❌ Blocked from entire treasury app
```

---

## PAYMENT EXECUTION WORKFLOW

1. **Requisition Approved** → Payment record created (status=pending)
2. **Treasury Staff** logs into treasury app
3. **Select Payment** → View pending payments
4. **Execute Payment**:
   - Select treasury fund to pay from
   - Choose payment method (mpesa/bank)
   - If OTP required → System sends OTP
   - Verify OTP
   - Confirm execution
5. **Payment Processed**:
   - Fund balance deducted
   - Ledger entry created
   - Payment status updated (completed/failed)
   - PaymentExecution record created
6. **If Balance Low** → Alert created, replenishment request triggered

---

## KEY DIFFERENCES

### Admin vs Treasury Staff
- **Admin**: Can view everything, manage users, but may not execute payments unless given explicit permission
- **Treasury Staff**: Focused on payment execution and fund operations

### Treasury Staff vs CFO
- **Treasury Staff**: Operational - execute payments, manage funds
- **CFO**: Strategic - approve variances, view high-level reports, financial oversight

### App Access vs Permissions
- **App Access** (`assigned_apps`): Controls which app you can see
- **Permissions** (`user_permissions`): Controls what you can DO within that app
- Both are required: Must have app assigned AND specific permissions

---

## CURRENT ISSUE YOU MENTIONED

You said: "treasury app seems varying for various users"

**This is BY DESIGN**. The variations come from:

1. **App Assignment** (`User.assigned_apps`)
   - If `treasury` not assigned → Cannot access at all
   - Checked by `RequireAppAccess` permission class

2. **Django Permissions** (`user.has_perm()`)
   - Controls CRUD operations (view/add/change/delete)
   - Checked by `DjangoModelPermissionsWithView`

3. **Role-Based Restrictions** (hardcoded in views)
   - Replenish funds: Only `role=treasury` or `role=admin`
   - Approve variances: Must be in CFO group
   - These are ADDITIONAL checks beyond Django permissions

4. **Superuser Bypass**
   - Superusers bypass ALL checks automatically
   - Django's built-in behavior

**Example**:
- User A (treasury staff): Can execute payments, replenish funds
- User B (requester): Cannot access treasury app at all
- User C (CFO): Can do everything treasury staff can + approve variances
- Superuser: Can do absolutely everything

This is the **designed security model** to ensure proper separation of duties and financial controls.
