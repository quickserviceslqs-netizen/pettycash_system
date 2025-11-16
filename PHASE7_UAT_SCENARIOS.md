# Phase 7 — UAT Scenarios

This document contains UAT scenarios, success criteria, and test accounts/fixtures for stakeholders to validate the Petty Cash Management System.

## Goals
- Validate end-to-end requisition → approval → payment → reconciliation flows.
- Confirm RBAC, no-self-approval, urgent fast-track, and CFO escalation behave as expected.
- Verify dashboard metrics, alerts, and reports match expected outcomes.

## Test Accounts / Fixtures
- requester@example.com — role: `staff` — belongs to Branch A
- branch_manager@example.com — role: `branch_manager` — Branch A
- treasury@example.com — role: `treasury` — Company-level
- admin@example.com — role: `admin` — superuser
- cfo@example.com — role: `cfo`

Create these users in staging with clear passwords and provide stakeholders a test login sheet.

## Core UAT Scenarios
1. Submit Requisition (Tier 1)
   - Create a requisition for `5,000.00` by `requester` from Branch A.
   - Expect workflow: branch_manager -> treasury.
   - Approve as branch_manager, then as treasury. Verify `Payment` created and `LedgerEntry` created on success.

2. Urgent Requisition Fast-track
   - Mark a requisition as `is_urgent=True` with threshold allowing fast-track.
   - Expect the requisition to skip intermediate approvers and arrive at final approver. Verify audit trail notes skipped roles.

3. No-Self-Approval
   - Requester must not be allowed to approve their own requisition. Attempt should fail.

4. Variance Adjustment Flow
   - Create a variance, submit for CFO approval, approve/reject flows, verify ledger adjustments.

5. Dashboard & Alerts
   - Trigger a fund below `reorder_level` and confirm an alert is created, email/notification sent.

6. Failure and Retry
   - Simulate a failing payment gateway response. Verify `Payment.mark_failed` increments `retry_count` and summary notifications appear.

## Acceptance Criteria
- Each scenario has pass/fail results captured in a UAT spreadsheet.
- No critical or high defects blocking core flows.
- Stakeholders sign-off on acceptance criteria in `PHASE7_ACCEPTANCE_CRITERIA.md`.

## Logistics
- UAT should be executed against the `staging` environment with a recent DB snapshot.
- Require backup before running any DB-affecting migration steps.

