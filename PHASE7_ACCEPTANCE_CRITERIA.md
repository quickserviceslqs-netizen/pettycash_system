# Phase 7 — Acceptance Criteria & Sign-off

Define concrete acceptance criteria for go/no-go decisions.

## Critical (must pass)
- End-to-end requisition → approval → payment → ledger reconciliation flow works in staging with realistic data.
- No-self-approval enforced; approver roles are correct and auditable.
- Migrations applied successfully to staging without data loss.
- No open critical or high-severity defects.

## High (should pass)
- Dashboard metrics match expected totals for sample data sets.
- Alerts fire for low funds and failed payments.
- OTP flow and retry logic behave securely.

## Medium/Low
- Performance: median dashboard load < 1s for typical dataset (10k records), 95th percentile < 3s.
- Load test: system sustains 500 concurrent simulated users with acceptable error rate (<1%).

## Sign-off
- All critical items verified by the product owner and finance lead.
- Security review completed and no outstanding critical findings.
- Migration & rollback plan approved by ops.

