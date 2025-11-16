# PHASE 5 - QUICK START GUIDE

## Prerequisites

```bash
cd c:\Users\ADMIN\pettycash_system
.\venv\Scripts\Activate.ps1
```

## Database Setup

```bash
# Apply all migrations
python manage.py migrate --settings=test_settings

# Verify tables created
python manage.py showmigrations --settings=test_settings
```

## Start Development Server

```bash
python manage.py runserver 0.0.0.0:8000 --settings=test_settings
```

## Access Points

### Admin Interface
```
URL: http://localhost:8000/admin/
Username: admin
Password: (create with: python manage.py createsuperuser --settings=test_settings)

Sections:
- Treasury
  - Treasury Funds
  - Payments
  - Payment Executions
  - Ledger Entries
  - Variance Adjustments
  - Replenishment Requests
```

### API Endpoints

**Base URL**: `http://localhost:8000/api/`

#### Treasury Funds
```
GET    /api/funds/                           List all funds
GET    /api/funds/{fund_id}/                 Get fund details
GET    /api/funds/{fund_id}/balance/         Get current balance
POST   /api/funds/{fund_id}/replenish/       Replenish fund (staff only)
       Body: {"amount": "50000.00"}
```

#### Payments
```
GET    /api/payments/                         List payments
POST   /api/payments/                         Create payment
       Body: {
           "requisition": "uuid",
           "amount": "5000.00",
           "method": "mpesa",
           "destination": "+254700000000",
           "otp_required": true
       }

GET    /api/payments/{payment_id}/            Get payment details
POST   /api/payments/{payment_id}/send_otp/   Send OTP
POST   /api/payments/{payment_id}/verify_otp/ Verify OTP
       Body: {"otp": "123456"}
POST   /api/payments/{payment_id}/execute/    Execute payment
       Body: {
           "gateway_reference": "REF123",
           "gateway_status": "success"
       }
POST   /api/payments/{payment_id}/reconcile/  Mark reconciled (staff)
POST   /api/payments/{payment_id}/record_variance/ Record variance
       Body: {
           "original_amount": "5000.00",
           "adjusted_amount": "4950.00",
           "reason": "Processing fee"
       }
```

#### Variance Adjustments
```
GET    /api/variances/                       List variances
GET    /api/variances/{variance_id}/         Get variance details
POST   /api/variances/{variance_id}/approve/ Approve variance (CFO only)
```

#### Replenishment Requests
```
GET    /api/replenishments/                  List requests
GET    /api/replenishments/{request_id}/     Get request details
```

#### Ledger Entries
```
GET    /api/ledger/                          List all ledger entries
GET    /api/ledger/{ledger_id}/              Get entry details
GET    /api/ledger/by_fund/?fund_id=...      Get entries for fund
```

## Testing with cURL/Postman

### 1. Get Available Funds
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/funds/
```

### 2. Create Payment
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "requisition": "requisition-uuid",
       "amount": "5000.00",
       "method": "mpesa",
       "destination": "+254700000000",
       "otp_required": true
     }' \
     http://localhost:8000/api/payments/
```

### 3. Send OTP
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/payments/payment-uuid/send_otp/
```

### 4. Verify OTP
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"otp": "123456"}' \
     http://localhost:8000/api/payments/payment-uuid/verify_otp/
```

### 5. Execute Payment
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "gateway_reference": "GATE123",
       "gateway_status": "success"
     }' \
     http://localhost:8000/api/payments/payment-uuid/execute/
```

## Running Tests

```bash
# Run all treasury tests
python manage.py test treasury --settings=test_settings -v 2

# Run specific test class
python manage.py test treasury.tests.test_payment_execution --settings=test_settings -v 2

# Run with coverage
coverage run --source='.' manage.py test treasury --settings=test_settings
coverage report
coverage html  # Creates htmlcov/index.html
```

## Validation Script

```bash
# Run validation (ensure migrations applied first)
python phase5_validation.py
```

Expected output:
```
[1/5] Creating test data...
✅ Created: Company, Region, Branch, Users, Fund

[2/5] Testing Payment Workflow...
✅ Segregation check passed
✅ Valid executor check passed
✅ Payment executed
✅ Fund deducted correctly
✅ Ledger entry created
✅ Payment status updated

[3/5] Testing Auto-Replenishment Trigger...
✅ Fund balance set below reorder level

[4/5] Testing OTP Service...
✅ OTP generated

[5/5] Testing Variance Tracking...
✅ Variance recorded

✅ ALL VALIDATION TESTS PASSED!
```

## Development Workflow

### 1. Setup
```bash
cd c:\Users\ADMIN\pettycash_system
.\venv\Scripts\Activate.ps1
python manage.py migrate --settings=test_settings
```

### 2. Create Test Data
```bash
python manage.py shell --settings=test_settings
>>> from organization.models import Company, Region, Branch
>>> company = Company.objects.create(name="TestCo", code="TC")
>>> region = Region.objects.create(company=company, name="Nairobi", code="NBO")
>>> branch = Branch.objects.create(region=region, name="HQ", code="HQ")
>>> from treasury.models import TreasuryFund
>>> from decimal import Decimal
>>> fund = TreasuryFund.objects.create(
...     company=company, region=region, branch=branch,
...     current_balance=Decimal('100000'), reorder_level=Decimal('50000')
... )
>>> exit()
```

### 3. Start Server
```bash
python manage.py runserver --settings=test_settings
```

### 4. Test via Admin or API
```bash
# In browser: http://localhost:8000/admin/
# Or via API: http://localhost:8000/api/
```

## Environment Variables

Required in `test_settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # Console only for testing
# Or use real email:
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'your-smtp-server'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email'
EMAIL_HOST_PASSWORD = 'your-password'
```

## Troubleshooting

### Issue: No such table
```
Solution: python manage.py migrate --settings=test_settings
```

### Issue: Import errors
```
Solution: Ensure PYTHONPATH includes project root:
set PYTHONPATH=%CD%
```

### Issue: Static files not loading
```bash
python manage.py collectstatic --settings=test_settings
```

### Issue: Database locked
```bash
# Delete and recreate
rm db.sqlite3
python manage.py migrate --settings=test_settings
```

## Files to Review

For understanding Phase 5:
- **Design**: PHASE5_OUTLINE.md
- **Implementation**: PHASE5_COMPLETION_REPORT.md
- **Quick Ref**: PHASE5_QUICK_SUMMARY.md
- **Final Status**: PHASE5_FINAL_STATUS.md
- **Code**: treasury/models.py, treasury/services/payment_service.py, treasury/views.py

## Documentation Structure

```
PHASE5_OUTLINE.md
├─ Purpose & Goals
├─ Data Models (6)
├─ Service Layer (3)
├─ API Endpoints
├─ Enforcement Rules
├─ Testing Strategy
└─ Rollout Checklist

PHASE5_COMPLETION_REPORT.md
├─ Executive Summary
├─ Deliverables (6 models, 3 services, 5 ViewSets)
├─ Enforcement Rules
├─ Test Coverage
├─ Architecture Diagram
├─ Security Features
├─ Files Modified/Created
└─ Sign-Off

PHASE5_FINAL_STATUS.md
├─ Deliverables Summary
├─ Implementation Details
├─ Security Implementation
├─ Verification Results
├─ Quality Metrics
└─ Sign-Off

SESSION_SUMMARY.md
├─ Part 1: Phase 4 Verification
├─ Part 2: Phase 5 Implementation
├─ Core Security Feature
├─ Key Implementation Details
├─ Deliverables
└─ Completion Status
```

## Next Steps

1. **Run Tests**: Execute all Phase 5 tests
2. **Code Review**: Review models, services, and views
3. **Integration**: Integrate with Phase 4 (approved requisitions)
4. **Deployment**: Deploy to staging environment
5. **Phase 6**: Initialize Treasury Dashboard & Reporting

## Contact & Support

For questions about Phase 5 implementation:
- Review PHASE5_COMPLETION_REPORT.md for technical details
- Check PHASE5_QUICK_SUMMARY.md for quick answers
- See treasury/models.py docstrings for model details
- Review treasury/services/payment_service.py for service logic

---

**Phase 5: Treasury Payment Execution** ✅ READY FOR TESTING
