# Security Testing Suite

## Overview
Comprehensive security testing for the Petty Cash Management System covering:
- Role-Based Access Control (RBAC)
- CSRF Protection
- OTP Validation
- SQL Injection Prevention
- XSS Prevention
- Input Validation

## Running Security Tests

### Run All Security Tests
```powershell
python manage.py test tests.security --settings=test_settings
```

### Run Specific Test Modules

```powershell
# RBAC Tests
python manage.py test tests.security.test_rbac --settings=test_settings

# CSRF Protection Tests
python manage.py test tests.security.test_csrf --settings=test_settings

# OTP Validation Tests
python manage.py test tests.security.test_otp --settings=test_settings

# Injection Prevention Tests
python manage.py test tests.security.test_injection --settings=test_settings
```

### Run Specific Test Cases

```powershell
# Test self-approval prevention
python manage.py test tests.security.test_rbac.ApprovalWorkflowSecurityTest.test_requester_cannot_self_approve --settings=test_settings

# Test CSRF protection
python manage.py test tests.security.test_csrf.CSRFProtectionTest.test_post_without_csrf_token_fails --settings=test_settings

# Test SQL injection prevention
python manage.py test tests.security.test_injection.SQLInjectionTest.test_sql_injection_in_search_parameter --settings=test_settings
```

## Test Coverage

### RBAC Tests (`test_rbac.py`)

**RequisitionAccessControlTest:**
- ✅ Unauthenticated users blocked from creating requisitions
- ✅ Branch staff can create own requisitions
- ✅ Users cannot view other branch requisitions
- ✅ Admins can view all requisitions

**ApprovalWorkflowSecurityTest:**
- ✅ Requesters cannot self-approve
- ✅ Unauthorized users cannot approve
- ✅ Authorized approvers can approve

**TreasuryAccessControlTest:**
- ✅ Non-treasury users cannot execute payments
- ✅ Treasury users can execute payments
- ✅ Requesters cannot execute own payments (segregation of duties)

**ReportingAccessControlTest:**
- ✅ Branch staff limited to own branch reports
- ✅ CFO can access company-wide reports
- ✅ Unauthenticated users denied report access

### CSRF Tests (`test_csrf.py`)

**CSRFProtectionTest:**
- ✅ POST without CSRF token fails
- ✅ POST with valid CSRF token succeeds
- ✅ PUT without CSRF token fails
- ✅ DELETE without CSRF token fails
- ✅ GET requests not affected by CSRF
- ✅ AJAX requests can use X-CSRFToken header

**CSRFExemptAPITest:**
- ✅ API token authentication exempt from CSRF

### OTP Tests (`test_otp.py`)

**OTPValidationTest:**
- ✅ Payment execution requires OTP
- ✅ Invalid OTP rejected
- ✅ OTP requests rate-limited
- ✅ Expired OTP rejected
- ✅ OTP single-use only

**OTPGenerationTest:**
- ✅ OTP is 6-digit numeric
- ✅ OTP is cryptographically random
- ✅ OTP stored hashed, not plaintext

### Injection Tests (`test_injection.py`)

**SQLInjectionTest:**
- ✅ Search parameters sanitized
- ✅ Transaction ID lookups parameterized
- ✅ Filter parameters use ORM
- ✅ Raw SQL uses parameters

**XSSPreventionTest:**
- ✅ Purpose field sanitizes script tags
- ✅ Content-Type headers prevent XSS
- ✅ X-Content-Type-Options: nosniff header present

**InputValidationTest:**
- ✅ Amount rejects negative values
- ✅ Amount validates decimal format
- ✅ Required fields enforced
- ✅ Field max length enforced
- ✅ Enum fields validate choices

## Security Checklist

### Authentication & Authorization
- [ ] All endpoints require authentication
- [ ] RBAC enforced at view level
- [ ] Branch/company scoping enforced
- [ ] Admin privileges properly segregated
- [ ] Session timeout configured
- [ ] Password complexity enforced

### Data Protection
- [ ] CSRF tokens on all state-changing operations
- [ ] OTP for sensitive operations
- [ ] Payment execution requires dual authorization
- [ ] Audit trail for all changes
- [ ] PII data encrypted at rest
- [ ] Secure password hashing (PBKDF2/Argon2)

### Input Validation
- [ ] All user input validated
- [ ] SQL injection prevented (ORM usage)
- [ ] XSS prevented (template auto-escape)
- [ ] File upload validation
- [ ] JSON schema validation
- [ ] Rate limiting on API endpoints

### Infrastructure Security
- [ ] HTTPS enforced (HSTS enabled)
- [ ] Security headers configured
- [ ] Database connections encrypted
- [ ] API keys rotated regularly
- [ ] Secrets not in version control
- [ ] Error messages don't leak info

### Compliance
- [ ] Audit logging enabled
- [ ] Data retention policies configured
- [ ] Access logs maintained
- [ ] Separation of duties enforced
- [ ] Multi-level approval workflows
- [ ] Financial reconciliation trails

## Common Security Issues & Fixes

### Issue: Self-Approval
**Risk**: High  
**Fix**: Implemented in workflow resolver - excludes requester from approver list

### Issue: Payment Executor Same as Requester
**Risk**: High  
**Fix**: Segregation of duties check in payment execution

### Issue: Missing CSRF Protection
**Risk**: Medium  
**Fix**: Django CSRF middleware enabled, tokens required on POST/PUT/DELETE

### Issue: Weak OTP
**Risk**: High  
**Fix**: 6-digit cryptographically random OTP, 5-minute expiry, single-use

### Issue: SQL Injection
**Risk**: Critical  
**Fix**: Django ORM parameterization, no raw SQL without params

### Issue: Branch Data Leakage
**Risk**: High  
**Fix**: QuerySet filtering by user's branch/company in all views

## Penetration Testing Notes

### Manual Testing Checklist
1. **Authentication Bypass**
   - Try accessing protected endpoints without login
   - Test session fixation
   - Test concurrent session handling

2. **Authorization Bypass**
   - Try accessing other user's data
   - Test horizontal privilege escalation
   - Test vertical privilege escalation

3. **Injection Attacks**
   - SQL injection in all input fields
   - XSS in text fields
   - Command injection in file uploads

4. **Business Logic**
   - Negative amounts
   - Duplicate transactions
   - Race conditions on approvals
   - Replay attacks on payments

### Recommended Tools
- **OWASP ZAP**: Automated vulnerability scanner
- **Burp Suite**: Manual penetration testing
- **SQLMap**: SQL injection testing
- **Nikto**: Web server scanner

## CI/CD Integration

### GitHub Actions Security Scan
```yaml
- name: Security Tests
  run: |
    python manage.py test tests.security --settings=test_settings --parallel
    
- name: Dependency Vulnerability Scan
  run: |
    pip install safety
    safety check --json
    
- name: Static Security Analysis
  run: |
    pip install bandit
    bandit -r . -f json -o bandit-report.json
```

## Reporting Security Issues

**DO NOT** open public GitHub issues for security vulnerabilities.

Contact: security@yourcompany.com

Include:
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Next Steps

After security testing:
1. Run full test suite and document results
2. Address any failing tests
3. Perform penetration testing on staging
4. Security audit by external firm
5. Document security controls for compliance
6. Train team on secure coding practices
