# PHASE 6: TREASURY DASHBOARD & REPORTING

**Version**: 1.0  
**Status**: Design & Implementation  
**Date**: 2025-11-16  
**Dependencies**: Phase 4 (Approvals), Phase 5 (Payments)

---

## Executive Summary

Phase 6 transforms Phase 5's API-only payment system into a complete **Treasury Dashboard & Reporting** suite. This phase adds:

1. **Interactive Treasury Dashboard** - Real-time fund status, payment tracking, alerts
2. **Payment Execution UI** - OTP 2FA workflow, payment forms, execution tracking
3. **Fund Management UI** - Balance cards, reorder levels, replenishment requests
4. **Comprehensive Reporting** - Payment analytics, fund utilization, variance trends
5. **Real-time Alerts** - Fund warnings, variance alerts, payment failures
6. **PDF Export** - Reports in multiple formats

**Target Users**:
- Treasury Staff: Execute payments, manage funds
- Finance Managers: Monitor fund utilization, approve variances
- CFOs/Group Controllers: Strategic reporting, trend analysis
- Department Heads: Fund balance visibility, budget tracking

---

## Architecture Overview

### Phase 6 Component Stack

```
┌─────────────────────────────────────────────────────────┐
│         PHASE 6: TREASURY DASHBOARD & REPORTING         │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─ PRESENTATION LAYER (HTML/Bootstrap5)               │
│  │  ├─ Dashboard UI (treasury/dashboard.html)           │
│  │  ├─ Payment Execution UI (treasury/payment_exec.html)│
│  │  ├─ Fund Management UI (treasury/funds.html)         │
│  │  ├─ Reports UI (reports/reports.html)                │
│  │  ├─ Variance Approval UI (treasury/variances.html)   │
│  │  └─ Alert Center UI (treasury/alerts.html)           │
│  │                                                       │
│  ├─ API LAYER (Django REST Framework)                  │
│  │  ├─ DashboardViewSet (aggregate metrics)             │
│  │  ├─ MetricsViewSet (fund health, payment stats)      │
│  │  ├─ AlertsViewSet (real-time alerts)                 │
│  │  ├─ ReportingViewSet (PDF, CSV export)               │
│  │  └─ PaymentTrackingViewSet (audit trail)             │
│  │                                                       │
│  ├─ SERVICE LAYER (Business Logic)                     │
│  │  ├─ DashboardService (aggregate calculations)        │
│  │  ├─ AlertService (trigger & notification)            │
│  │  ├─ ReportService (generate & export)                │
│  │  └─ ForecastService (replenishment prediction)       │
│  │                                                       │
│  ├─ DATA LAYER (Models & ORM)                          │
│  │  ├─ TreasuryDashboard (cache for perf)               │
│  │  ├─ DashboardMetric (historical metrics)             │
│  │  ├─ Alert (alert triggers & history)                 │
│  │  ├─ PaymentTracking (enhanced audit trail)           │
│  │  └─ FundForecast (replenishment predictions)         │
│  │                                                       │
│  └─ EXISTING (Phase 4-5 Integration)                   │
│     ├─ Requisition (Phase 4)                            │
│     ├─ Payment (Phase 5)                                │
│     ├─ TreasuryFund (Phase 5)                           │
│     ├─ VarianceAdjustment (Phase 5)                     │
│     └─ LedgerEntry (Phase 5)                            │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

## Phase 6 Features

### Feature 1: Treasury Dashboard

**Location**: `/treasury/dashboard/`

#### Fund Status Cards
```
┌─────────────────────────────────────────────────┐
│ FUND NAME: Mumbai Branch Operating Fund         │
├─────────────────────────────────────────────────┤
│ Current Balance:      ₹2,500,000                │
│ Reorder Level:        ₹1,000,000                │
│ Status:               OK ✓ (75% utilization)   │
│ Last Updated:         2025-11-16 14:30:00      │
│ Total Transactions:   42 (this period)         │
│ Last Replenished:     2025-11-10               │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ FUND NAME: Delhi Payroll Fund                   │
├─────────────────────────────────────────────────┤
│ Current Balance:      ₹850,000                  │
│ Reorder Level:        ₹1,000,000                │
│ Status:               WARNING ⚠ (Low balance)  │
│ Last Updated:         2025-11-16 14:30:00      │
│ Total Transactions:   87 (this period)         │
│ Replenishment:        PENDING (Auto-triggered) │
└─────────────────────────────────────────────────┘
```

**Data Displayed**:
- Fund name, company, region, branch
- Current balance (real-time)
- Reorder level threshold
- Utilization % (balance / capacity)
- Status indicator (OK/Warning/Critical)
- Last replenished date
- Transaction count (daily/weekly/monthly)
- Quick links: View history, Execute payment, Request replenishment

**Status Logic**:
- **OK** (Green): Balance > reorder_level + 500K
- **WARNING** (Yellow): Balance between reorder_level and reorder_level + 500K
- **CRITICAL** (Red): Balance < reorder_level

#### Payment Execution Panel
```
┌─────────────────────────────────────────────────┐
│ PENDING PAYMENTS (Ready to Execute)             │
├─────────────────────────────────────────────────┤
│ ☐ REQ-001-2025  ₹50,000   |  Execute | Details │
│ ☐ REQ-005-2025  ₹125,000  |  Execute | Details │
│ ☐ REQ-012-2025  ₹75,000   |  Execute | Details │
│                                                  │
│ Total Pending: ₹250,000 (3 payments)            │
└─────────────────────────────────────────────────┘

[Status Timeline]
Draft → Approved → Awaiting Execution → Success
```

**Functionality**:
- List all approved requisitions awaiting payment execution
- Bulk select for batch processing
- Quick execute button (initiates OTP flow)
- Click for full payment details
- Status timeline visualization

#### Payment History Widget
```
┌─────────────────────────────────────────────────┐
│ RECENT PAYMENT EXECUTIONS                       │
├─────────────────────────────────────────────────┤
│ REQ-048-2025  ₹100,000  Success    2m ago      │
│ REQ-047-2025  ₹50,000   Success    15m ago     │
│ REQ-046-2025  ₹75,000   Failed     1h ago      │
│ REQ-045-2025  ₹125,000  Success    2h ago      │
└─────────────────────────────────────────────────┘
```

**Data**:
- Requisition ID
- Amount
- Status (Success/Failed/Pending)
- Timestamp
- Click for audit trail

#### Alerts & Notifications
```
┌─────────────────────────────────────────────────┐
│ ACTIVE ALERTS                                   │
├─────────────────────────────────────────────────┤
│ ⚠ Delhi Payroll Fund balance critical           │
│   Balance: ₹850K | Reorder: ₹1M                │
│                                                  │
│ ⚠ Payment REQ-046 execution failed               │
│   Error: Gateway timeout | Retry in 2h 15m     │
│                                                  │
│ ℹ Variance approved: REQ-042                     │
│   Variance: +₹5,000 | Approved by CFO           │
│                                                  │
│ ℹ Replenishment approved: Delhi Fund             │
│   Amount: ₹500,000 | Status: Funding           │
└─────────────────────────────────────────────────┘
```

**Alert Types**:
- Fund balance warnings (Critical/Low)
- Payment failures (retry count exceeded)
- Variance approvals (CFO)
- Replenishment approvals
- OTP verification failures
- Execution delays

---

### Feature 2: Payment Execution UI

**Location**: `/treasury/payment-execute/{id}/`

#### Payment Execution Flow

```
STEP 1: SELECT PAYMENT
┌─────────────────────────────────────────────────┐
│ Requisition: REQ-001-2025                       │
│ Amount: ₹50,000                                 │
│ Purpose: Office Supplies                        │
│ Origin: Mumbai Branch                           │
│ Status: Approved                                │
│ [PROCEED TO STEP 2]                             │
└─────────────────────────────────────────────────┘

STEP 2: SEND OTP
┌─────────────────────────────────────────────────┐
│ 2-Factor Authentication Required                │
│ OTP will be sent to: user@company.com          │
│ [SEND OTP]  [CANCEL]                           │
│                                                  │
│ Status: Sent to email (check spam folder)      │
└─────────────────────────────────────────────────┘

STEP 3: VERIFY OTP
┌─────────────────────────────────────────────────┐
│ Enter 6-digit OTP:  [_ _ _ _ _ _]               │
│ OTP expires in: 4:59 minutes                    │
│ [VERIFY]  [RESEND]  [CANCEL]                   │
│                                                  │
│ Status: Awaiting verification                  │
└─────────────────────────────────────────────────┘

STEP 4: CONFIRM & EXECUTE
┌─────────────────────────────────────────────────┐
│ PAYMENT DETAILS                                 │
│ ─────────────────────────────────────           │
│ Requisition ID: REQ-001-2025                    │
│ Amount: ₹50,000                                 │
│ Fund: Mumbai Operating Fund                     │
│ Executor: John Doe (Treasury)                   │
│ 2FA Status: Verified ✓                          │
│ IP Address: 192.168.1.100                       │
│ User Agent: Mozilla/5.0 (Windows)              │
│                                                  │
│ [EXECUTE PAYMENT] [CANCEL]                     │
│                                                  │
│ ⚠ This action is irreversible                  │
└─────────────────────────────────────────────────┘

STEP 5: EXECUTION RESULT
┌─────────────────────────────────────────────────┐
│ ✓ PAYMENT EXECUTED SUCCESSFULLY                 │
│                                                  │
│ Execution Details:                              │
│ ├─ Execution ID: EXE-12345-2025                │
│ ├─ Gateway Reference: GW-98765-2025            │
│ ├─ Amount: ₹50,000                              │
│ ├─ Timestamp: 2025-11-16 14:30:00              │
│ ├─ Status: Success                              │
│ └─ Fund Balance: ₹2,450,000                     │
│                                                  │
│ Next: Payment will reconcile after 24h          │
│                                                  │
│ [VIEW DETAILS] [PRINT] [BACK TO DASHBOARD]    │
└─────────────────────────────────────────────────┘
```

#### Implementation Details

**Session State Management**:
```python
# Session keys
session['payment_execution'] = {
    'payment_id': 'uuid',
    'step': 1,  # 1=select, 2=send_otp, 3=verify, 4=confirm, 5=result
    'otp_sent_time': timestamp,
    'otp_verified': False,
    'otp_verified_time': timestamp,
    'ip_address': request.META['REMOTE_ADDR'],
    'user_agent': request.META['HTTP_USER_AGENT'],
}
```

**Security Checks**:
- ✅ User must be treasury staff (role check)
- ✅ Payment must exist and status='executing'
- ✅ Executor ≠ requester (segregation)
- ✅ OTP must be verified within 5 minutes
- ✅ IP address captured for audit
- ✅ User agent captured for audit
- ✅ Session-based tracking to prevent double-execution

---

### Feature 3: Fund Management UI

**Location**: `/treasury/funds/`

```
┌─────────────────────────────────────────────────────┐
│ TREASURY FUND MANAGEMENT                            │
├─────────────────────────────────────────────────────┤
│                                                      │
│ [CREATE NEW FUND] [IMPORT FUNDS] [EXPORT]          │
│                                                      │
│ Filter: Company [ ] Region [ ] Branch [ ]           │
│         Status [OK/Warning/Critical]                │
│                                                      │
│ FUND LISTING:                                       │
│                                                      │
│ Fund Name         Balance    Reorder  Status  Act.  │
│ ───────────────────────────────────────────────────│
│ Mumbai Op.Fund   ₹2.5M      ₹1.0M   OK     ✓      │
│ Delhi Payroll    ₹850K      ₹1.0M   ⚠      ✓      │
│ Bangalore HQ     ₹5.2M      ₹2.0M   OK     ✓      │
│ Kolkata Field    ₹250K      ₹500K   ⚠      ✓      │
│                                                      │
│ [Edit] [View History] [Replenish] [More]           │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Operations**:
- View all funds with current balance
- Filter by company, region, branch, status
- Click to view fund history (all transactions)
- Request replenishment
- View transactions (ledger entries)
- Download transaction history

---

### Feature 4: Variance Tracking UI

**Location**: `/treasury/variances/`

```
┌─────────────────────────────────────────────────────┐
│ VARIANCE MANAGEMENT                                 │
├─────────────────────────────────────────────────────┤
│                                                      │
│ Filter: Status [Pending/Approved/Rejected]          │
│         CFO Approver [All/Jane Smith]               │
│         Date Range [From ____] [To ____]            │
│                                                      │
│ PENDING VARIANCES (CFO Approval):                   │
│                                                      │
│ REQ-042  Payment  ₹100K  Original:₹95K  Δ:+₹5K     │
│          Status: Pending Approval                   │
│          Submitted: 2h ago by Treasury               │
│          [APPROVE] [REJECT] [VIEW DETAILS]         │
│                                                      │
│ REQ-039  Payment  ₹50K   Original:₹50K  Δ:+₹0      │
│          Status: Pending Approval                   │
│          Submitted: 3h ago by Treasury               │
│          [APPROVE] [REJECT] [VIEW DETAILS]         │
│                                                      │
│ APPROVED VARIANCES:                                 │
│                                                      │
│ REQ-035  Payment  ₹75K   Original:₹75K  Δ:-₹2K     │
│          Approved: 1d ago by CFO Jane Smith        │
│          Notes: "Gateway discount applied"         │
│          [VIEW DETAILS]                             │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Functionality**:
- List pending variances for CFO approval
- Show original amount, actual amount, variance
- CFO can approve or reject with optional notes
- View variance history (approved/rejected)
- Filter by status, approver, date range
- Click for full audit trail

---

### Feature 5: Reporting & Analytics

**Location**: `/reports/treasury/`

#### Dashboard Reports

```
┌─────────────────────────────────────────────────────┐
│ TREASURY ANALYTICS DASHBOARD                        │
├─────────────────────────────────────────────────────┤
│                                                      │
│ DATE RANGE: [From 2025-01-01] [To 2025-11-16]     │
│ EXPORT: [PDF] [CSV] [Excel]                        │
│                                                      │
│ ┌─ PAYMENT VOLUME ──────────────────────────┐     │
│ │                                             │     │
│ │  Total Payments:    847                    │     │
│ │  Total Amount:      ₹45,250,000           │     │
│ │  Avg per Payment:   ₹53,421               │     │
│ │  Success Rate:      98.2%                 │     │
│ │  Failed/Retried:    15                    │     │
│ │                                             │     │
│ │  [Chart: Payment volume over time]        │     │
│ └─────────────────────────────────────────────┘     │
│                                                      │
│ ┌─ FUND UTILIZATION ────────────────────────┐     │
│ │                                             │     │
│ │  Total Funds:         12 active            │     │
│ │  Total Balance:       ₹22,500,000         │     │
│ │  Avg Utilization:     72%                 │     │
│ │  Funds Below Reorder: 2                   │     │
│ │  Funds Critical:      0                   │     │
│ │                                             │     │
│ │  [Chart: Fund balance by location]        │     │
│ └─────────────────────────────────────────────┘     │
│                                                      │
│ ┌─ VARIANCE ANALYSIS ───────────────────────┐     │
│ │                                             │     │
│ │  Total Variances:     23                   │     │
│ │  Total Variance $:    ₹47,500             │     │
│ │  Avg Variance:        ₹2,065              │     │
│ │  Positive:            12 (+₹32,000)       │     │
│ │  Negative:            11 (-₹15,500)       │     │
│ │  Pending Approval:    2                   │     │
│ │                                             │     │
│ │  [Chart: Variance trend over time]        │     │
│ └─────────────────────────────────────────────┘     │
│                                                      │
│ ┌─ REPLENISHMENT FORECAST ──────────────────┐     │
│ │                                             │     │
│ │  Requested (Pending): ₹1,500,000          │     │
│ │  Requested (Approved):₹2,000,000          │     │
│ │  Auto-triggered:      3 funds              │     │
│ │                                             │     │
│ │  Forecast (30 days):  ₹2,500,000 needed  │     │
│ │                                             │     │
│ │  [Chart: Replenishment forecast]          │     │
│ └─────────────────────────────────────────────┘     │
│                                                      │
└─────────────────────────────────────────────────────┘
```

#### Detailed Reports

**Payment Summary Report**
```
Period: 2025-11-01 to 2025-11-16
Total Payments: 847 | Amount: ₹45,250,000

By Origin Type:
├─ Branch: 520 payments | ₹28,500,000 (63%)
├─ HQ: 250 payments | ₹14,000,000 (31%)
└─ Field: 77 payments | ₹2,750,000 (6%)

By Status:
├─ Success: 831 | ₹44,410,000 (98.1%)
├─ Failed: 12 | ₹580,000 (1.3%)
├─ Pending: 4 | ₹260,000 (0.6%)

By Region:
├─ North: 312 | ₹18,500,000
├─ South: 285 | ₹16,000,000
├─ East: 150 | ₹7,500,000
└─ West: 100 | ₹3,250,000
```

**Fund Health Report**
```
Fund Status Overview:

Fund Name           Balance    Capacity  Util%  Status
─────────────────────────────────────────────────────
Mumbai Branch      ₹2,500K     ₹3,500K   71%   OK
Delhi Payroll      ₹850K       ₹2,000K   42%   ⚠ Low
Bangalore HQ       ₹5,200K     ₹8,000K   65%   OK
...

Critical Funds (< Reorder):
├─ Delhi Payroll: ₹850K (below ₹1.0M reorder)
├─ Kolkata Field: ₹250K (below ₹500K reorder)

Replenishment Status:
├─ Pending: ₹1,500,000 (3 requests)
├─ Approved: ₹2,000,000 (2 requests, funding)
└─ Rejected: ₹500,000 (1 request)
```

**Variance Analysis Report**
```
Period: 2025-11-01 to 2025-11-16
Total Variances: 23 | Total Amount: ₹47,500

Variance Breakdown:
├─ Positive (+): 12 variances | +₹32,000
├─ Negative (-): 11 variances | -₹15,500

Pending CFO Approval: 2 | ₹8,500

Top Variances:
├─ REQ-042: +₹5,000 (Gateway discount)
├─ REQ-038: +₹4,200 (Early payment benefit)
├─ REQ-015: -₹3,500 (Gateway fee increase)
└─ REQ-008: -₹2,800 (Exchange rate loss)

CFO Approved:
├─ Total Approved: 21
├─ Total Amount: ₹39,000
└─ Avg Time to Approval: 2.4 hours
```

---

### Feature 6: Real-time Alerts System

**Alert Types & Triggers**:

| Alert Type | Trigger | Recipient | Action |
|-----------|---------|-----------|--------|
| **Critical Fund Balance** | Balance < reorder_level | Treasury + Manager | Replenish immediately |
| **Low Fund Balance** | Balance < reorder + 500K | Manager + Finance | Request replenishment |
| **Payment Failed** | Retry count exceeded | Treasury + Manager | Manual investigation |
| **Payment Timeout** | Execution > 1 hour | Treasury + Manager | Retry or escalate |
| **OTP Expiration** | OTP > 5 min | User | Resend OTP |
| **Variance Alert** | Variance > threshold | CFO + Manager | Review & approve |
| **Replenishment Auto-trigger** | Auto-created on low balance | Treasury + Manager | Approve funding |
| **Execution Delay** | Execution > SLA | Manager | Escalate |
| **System Error** | Transaction rollback | Admin | Technical review |

**Alert Schema**:
```python
class Alert(models.Model):
    id = UUIDField()
    alert_type = CharField(choices=[...])  # Critical, Warning, Info
    severity = CharField(choices=['Critical', 'High', 'Medium', 'Low'])
    title = CharField()
    message = TextField()
    related_payment = ForeignKey(Payment)
    related_fund = ForeignKey(TreasuryFund)
    created_at = DateTimeField()
    acknowledged_at = DateTimeField(null=True)
    acknowledged_by = ForeignKey(User, null=True)
    resolved_at = DateTimeField(null=True)
    resolved_by = ForeignKey(User, null=True)
    resolution_notes = TextField(null=True)
    email_sent = BooleanField(default=False)
    email_sent_at = DateTimeField(null=True)
```

**Alert Center UI** (`/treasury/alerts/`):
```
┌─────────────────────────────────────────────────────┐
│ ALERT CENTER                                        │
├─────────────────────────────────────────────────────┤
│                                                      │
│ Filter: Severity [All/Critical/High/Medium]         │
│         Status [Unresolved/Resolved]                │
│         Type [All/Fund/Payment/System]              │
│                                                      │
│ UNRESOLVED ALERTS (5):                              │
│                                                      │
│ 🔴 CRITICAL | Delhi Fund balance critical           │
│    Balance ₹850K below reorder ₹1M                 │
│    Created: 2h ago | [RESOLVE] [SNOOZE 1h]        │
│                                                      │
│ 🟠 HIGH | Payment REQ-046 execution failed          │
│    Gateway timeout | Retried 2/3 times              │
│    Created: 1h ago | [RETRY] [ESCALATE]            │
│                                                      │
│ 🟡 MEDIUM | Variance REQ-042 pending CFO approval  │
│    +₹5K variance | Waiting 3h                       │
│    Created: 3h ago | [VIEW] [DISMISS]              │
│                                                      │
│ RESOLVED ALERTS (12):                               │
│                                                      │
│ ✓ Payment REQ-041 executed successfully             │
│   Resolved: 30m ago                                  │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## Database Models

### New Models for Phase 6

#### 1. TreasuryDashboard (Cache)
```python
class TreasuryDashboard(models.Model):
    id = UUIDField(primary_key=True)
    company = ForeignKey(Company)
    region = ForeignKey(Region)
    branch = ForeignKey(Branch, null=True)
    
    # Aggregated metrics (cached, updated hourly)
    total_funds = IntegerField()
    total_balance = DecimalField()
    total_utilization_pct = DecimalField()
    funds_below_reorder = IntegerField()
    funds_critical = IntegerField()
    
    # Payment metrics
    payments_today = IntegerField()
    payments_this_week = IntegerField()
    payments_this_month = IntegerField()
    total_amount_today = DecimalField()
    total_amount_this_week = DecimalField()
    total_amount_this_month = DecimalField()
    
    # Alerts
    active_alerts = IntegerField()
    critical_alerts = IntegerField()
    
    # Replenishment
    pending_replenishments = IntegerField()
    pending_replenishment_amount = DecimalField()
    
    # Variance
    pending_variances = IntegerField()
    pending_variance_amount = DecimalField()
    
    # Metadata
    last_updated = DateTimeField(auto_now=True)
    calculated_at = DateTimeField()
```

#### 2. DashboardMetric (Historical)
```python
class DashboardMetric(models.Model):
    id = UUIDField(primary_key=True)
    dashboard = ForeignKey(TreasuryDashboard)
    metric_type = CharField()  # 'fund_balance', 'payment_volume', 'utilization', etc.
    metric_date = DateField()
    metric_hour = IntegerField(null=True)  # 0-23 for hourly metrics
    value = DecimalField()
    
    class Meta:
        indexes = [
            Index(fields=['dashboard', 'metric_type', 'metric_date']),
            Index(fields=['metric_type', 'metric_date']),
        ]
```

#### 3. Alert
```python
class Alert(models.Model):
    SEVERITY_CHOICES = [
        ('Critical', 'Critical'),
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
    ]
    
    TYPE_CHOICES = [
        ('fund_critical', 'Fund Balance Critical'),
        ('fund_low', 'Fund Balance Low'),
        ('payment_failed', 'Payment Failed'),
        ('payment_timeout', 'Payment Timeout'),
        ('otp_expired', 'OTP Expired'),
        ('variance_pending', 'Variance Pending'),
        ('replenishment_auto', 'Replenishment Auto-triggered'),
        ('execution_delay', 'Execution Delay'),
        ('system_error', 'System Error'),
    ]
    
    id = UUIDField(primary_key=True)
    alert_type = CharField(choices=TYPE_CHOICES)
    severity = CharField(choices=SEVERITY_CHOICES)
    title = CharField(max_length=255)
    message = TextField()
    
    # Related records
    related_payment = ForeignKey(Payment, null=True, on_delete=models.SET_NULL)
    related_fund = ForeignKey(TreasuryFund, null=True, on_delete=models.SET_NULL)
    related_variance = ForeignKey(VarianceAdjustment, null=True, on_delete=models.SET_NULL)
    
    # Timestamps
    created_at = DateTimeField(auto_now_add=True)
    acknowledged_at = DateTimeField(null=True)
    acknowledged_by = ForeignKey(User, null=True, related_name='acknowledged_alerts', on_delete=models.SET_NULL)
    resolved_at = DateTimeField(null=True)
    resolved_by = ForeignKey(User, null=True, related_name='resolved_alerts', on_delete=models.SET_NULL)
    resolution_notes = TextField(null=True)
    
    # Email tracking
    email_sent = BooleanField(default=False)
    email_sent_at = DateTimeField(null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            Index(fields=['alert_type', 'severity', 'created_at']),
            Index(fields=['resolved_at']),
        ]
```

#### 4. PaymentTracking (Enhanced Audit)
```python
class PaymentTracking(models.Model):
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('otp_sent', 'OTP Sent'),
        ('otp_verified', 'OTP Verified'),
        ('executing', 'Executing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('reconciled', 'Reconciled'),
    ]
    
    id = UUIDField(primary_key=True)
    payment = OneToOneField(Payment, on_delete=models.CASCADE)
    
    # Timeline
    created_at = DateTimeField(auto_now_add=True)
    otp_sent_at = DateTimeField(null=True)
    otp_verified_at = DateTimeField(null=True)
    execution_started_at = DateTimeField(null=True)
    execution_completed_at = DateTimeField(null=True)
    reconciliation_started_at = DateTimeField(null=True)
    reconciliation_completed_at = DateTimeField(null=True)
    
    # Performance metrics
    total_execution_time = DurationField(null=True)
    otp_verification_time = DurationField(null=True)
    
    # Current status
    current_status = CharField(choices=STATUS_CHOICES)
    status_message = TextField(null=True)
```

#### 5. FundForecast (Replenishment Prediction)
```python
class FundForecast(models.Model):
    id = UUIDField(primary_key=True)
    fund = ForeignKey(TreasuryFund)
    forecast_date = DateField()
    
    # Predicted metrics
    predicted_balance = DecimalField()
    predicted_utilization_pct = DecimalField()
    predicted_daily_expense = DecimalField()
    days_until_reorder = IntegerField()
    
    # Recommendation
    needs_replenishment = BooleanField()
    recommended_replenishment_amount = DecimalField()
    confidence_level = DecimalField()  # 0-100%
    
    # Metadata
    calculated_at = DateTimeField()
    forecast_horizon_days = IntegerField()  # 7, 14, 30
    
    class Meta:
        unique_together = ['fund', 'forecast_date']
        indexes = [
            Index(fields=['fund', 'forecast_date']),
            Index(fields=['needs_replenishment', 'forecast_date']),
        ]
```

---

## API Endpoints (Phase 6 New)

### Dashboard API
```
GET  /api/dashboard/                      - Get dashboard summary
GET  /api/dashboard/metrics/              - Get metrics data
POST /api/dashboard/refresh/              - Force refresh cache

GET  /api/dashboard/funds/status/         - Fund status cards
GET  /api/dashboard/payments/pending/     - Pending payments
GET  /api/dashboard/payments/recent/      - Recent payments
GET  /api/dashboard/alerts/active/        - Active alerts
GET  /api/dashboard/alerts/history/       - Alert history
POST /api/dashboard/alerts/{id}/acknowledge/ - Acknowledge alert
POST /api/dashboard/alerts/{id}/resolve/     - Resolve alert
```

### Payment Execution UI API
```
GET  /api/payment/{id}/execution-status/ - Get execution status
POST /api/payment/{id}/send-otp/         - Send OTP
POST /api/payment/{id}/verify-otp/       - Verify OTP
POST /api/payment/{id}/execute/          - Execute payment
GET  /api/payment/{id}/execution-history/ - Execution history
```

### Reporting API
```
GET  /api/reports/payment-summary/       - Payment summary
GET  /api/reports/fund-health/           - Fund health
GET  /api/reports/variance-analysis/     - Variance analysis
GET  /api/reports/forecast/              - Replenishment forecast
POST /api/reports/export/                - Export report (PDF/CSV)
```

---

## Implementation Phases

### Phase 6.1: Models & Services (Days 1-2)
- ✅ Create 5 new models (TreasuryDashboard, DashboardMetric, Alert, PaymentTracking, FundForecast)
- ✅ Create AlertService with email notifications
- ✅ Create DashboardService with caching strategy
- ✅ Create ReportService for PDF/CSV generation
- ✅ Database migrations

### Phase 6.2: API Endpoints (Days 2-3)
- ✅ DashboardViewSet with 15+ endpoints
- ✅ AlertsViewSet with CRUD + acknowledge/resolve
- ✅ PaymentTrackingViewSet with history
- ✅ ReportingViewSet with exports
- ✅ URL configuration

### Phase 6.3: UI Templates (Days 3-4)
- ✅ base.html updates (navigation, alerts)
- ✅ dashboard.html (fund cards, payments, alerts)
- ✅ payment_execute.html (OTP flow)
- ✅ funds.html (fund list, history)
- ✅ variances.html (variance approval)
- ✅ alerts.html (alert center)
- ✅ reports.html (analytics dashboard)

### Phase 6.4: JavaScript & Frontend Logic (Days 4-5)
- ✅ Dashboard auto-refresh (every 5 minutes)
- ✅ Real-time alert notifications
- ✅ Payment OTP countdown timer
- ✅ AJAX form submissions
- ✅ Chart.js visualizations

### Phase 6.5: Testing & Verification (Days 5-6)
- ✅ Unit tests for services
- ✅ API endpoint tests
- ✅ UI rendering tests
- ✅ Alert trigger tests
- ✅ Report generation tests
- ✅ Load testing

### Phase 6.6: Documentation & Sign-off (Day 6)
- ✅ Completion report
- ✅ Verification checklist
- ✅ User guide
- ✅ Phase 7 outline

---

## Security Considerations

### Data Protection
- ✅ All dashboard data filtered by company/region/branch
- ✅ Role-based access (treasury, finance, cfo only)
- ✅ Audit trail for all actions
- ✅ Variance approvals require CFO role
- ✅ Alert acknowledgment tracked

### Transaction Security
- ✅ Payment execution atomic with locking
- ✅ OTP verified within 5-minute window
- ✅ Executor ≠ requester enforced
- ✅ IP address + user agent captured
- ✅ Double-execute prevention via session state

### Reporting Security
- ✅ PDF watermarked with user/date/time
- ✅ CSV exports require authorization
- ✅ Sensitive data (OTP, etc.) excluded from reports
- ✅ Export logs maintained for audit

---

## Performance Optimization

### Caching Strategy
```
TreasuryDashboard: Cache for 1 hour
├─ Invalidated on: Payment execution, Fund replenishment, Variance approval
├─ Updated hourly: Background job (celery task or Django Q)

DashboardMetric: Aggregated daily
├─ Calculated: 00:05 each day (after EOD reconciliation)
├─ Updated hourly: Incremental updates

Alert cache: Real-time
├─ Invalidated immediately on new alert
├─ Kept for 7 days, then archived
```

### Database Optimization
```sql
-- Critical indexes for dashboard queries
CREATE INDEX idx_payment_status_created ON payment(status, created_at DESC);
CREATE INDEX idx_ledger_fund_created ON ledger_entry(treasury_fund_id, created_at DESC);
CREATE INDEX idx_alert_type_severity ON alert(alert_type, severity, resolved_at);
CREATE INDEX idx_variance_status_created ON variance_adjustment(status, created_at DESC);
```

### API Response Time Targets
- Dashboard summary: < 200ms
- Fund status cards: < 300ms
- Recent payments: < 500ms
- Alerts: < 100ms
- Report generation: < 2s

---

## Testing Strategy

### Unit Tests (Models & Services)
```
test_alert_creation()
test_alert_escalation()
test_dashboard_metrics_calculation()
test_fund_forecast_accuracy()
test_report_generation()
test_email_notification()
```

### Integration Tests (API & UI)
```
test_payment_execution_flow()
test_otp_verification()
test_variance_approval_workflow()
test_replenishment_auto_trigger()
test_alert_notification()
test_report_export()
```

### UI Tests (Templates)
```
test_dashboard_rendering()
test_payment_execute_form()
test_variance_approval_form()
test_alert_center_display()
test_responsive_design()
```

### Load Tests
```
1000 concurrent users accessing dashboard
100 concurrent payment executions
10000 alert notifications
Large report generation (100K rows)
```

---

## Success Criteria

### Functionality ✅
- [ ] Dashboard displays real-time fund status
- [ ] Payment execution OTP flow works end-to-end
- [ ] Alerts trigger automatically on fund critical
- [ ] Variance approval workflow implemented
- [ ] Reports generate with correct calculations
- [ ] All 6 features working without errors

### Performance ✅
- [ ] Dashboard loads < 500ms
- [ ] API responses < 200ms
- [ ] Report generation < 2s
- [ ] No N+1 queries in API

### Security ✅
- [ ] No unauthorized access to other companies' data
- [ ] OTP verification enforced
- [ ] All actions audited
- [ ] Role-based access working
- [ ] No payment double-execution possible

### UX ✅
- [ ] Dashboard intuitive and responsive
- [ ] Forms have validation feedback
- [ ] Alerts clearly visible
- [ ] Payment execution wizard is user-friendly
- [ ] Reports easy to export

---

## Phase 7 Preview

After Phase 6 completion:

**Phase 7: Advanced Treasury Features**
- Bulk payment processing
- Payment scheduling (future dates)
- Multi-currency support
- Invoice matching & auto-posting
- GSTR/GST compliance
- Bank reconciliation automation
- Mobile app (iOS/Android)

---

## Dependencies & Prerequisites

✅ **Phase 4**: Requisition workflow, approvals
✅ **Phase 5**: Payment models, execution service, 2FA OTP

**External Dependencies**:
- Django 4.x
- Django REST Framework
- PostgreSQL 12+
- Celery (optional, for background tasks)
- ReportLab (PDF generation)
- Pandas (data analysis)
- Chart.js (frontend charts)
- Bootstrap 5

**Configuration Needed**:
- Email SMTP settings (for OTP & alerts)
- Celery broker (if using background tasks)
- Static files configuration

---

## Rollback Plan

If Phase 6 encounters critical issues:

1. **Data-only rollback**: Delete new records from Phase 6 tables
2. **Code rollback**: Revert to Phase 5 commit (Phase 4 verified working)
3. **Database rollback**: Use backup from pre-Phase 6
4. **User communication**: "Dashboard temporarily unavailable, using API"

---

## Conclusion

Phase 6 transforms Petty Cash System into a fully functional Treasury Dashboard & Reporting platform. With 6 major features, 15+ API endpoints, and comprehensive UI, this phase enables users to:

1. **Monitor** fund health in real-time
2. **Execute** payments securely with 2FA
3. **Track** payment status with audit trail
4. **Approve** variances with confidence
5. **Analyze** trends via comprehensive reports
6. **Respond** to alerts immediately

**Estimated Effort**: 40-50 developer hours  
**Target Completion**: 6 business days  
**Ready to Begin**: ✅

