# Phase 7 Security Checklist

Run these checks in staging before sign-off.

- RBAC
  - Verify only expected roles can approve payment and access treasury endpoints.
  - Test No-Self-Approval: requester cannot approve their own requisition.

- Authentication / Session
  - Verify session cookies have `Secure` and `HttpOnly` flags.
  - Verify password resets and account lockout behavior.

- CSRF
  - Confirm all POST/PUT/DELETE endpoints are protected by CSRF tokens (forms) or proper Authorization headers for APIs.

- Input Validation
  - Ensure server-side validation for amount, phone numbers, and free-text fields to prevent injection.

- SQL Injection
  - Run basic SQLi tests against endpoints that accept user input; ensure ORM parameterization is used.

- OTP Security
  - Verify rate-limiting on OTP attempts and retry behavior; lock out after configured retries.

- Transport Security
  - Ensure TLS everywhere in staging; redirect HTTP to HTTPS.

- Logging & Secrets
  - Ensure no secrets are logged; verify Sentry scrubbing settings.

- Pen-testing
  - Run an automated scan (e.g., OWASP ZAP) and a quick manual review for privilege escalation vectors.

For each check, capture results in the UAT spreadsheet and escalate any critical issues.
