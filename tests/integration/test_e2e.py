"""
End-to-End Integration Tests
Phase 7: Complete workflow testing
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from tests.integration.base import IntegrationTestBase
from transactions.models import ApprovalTrail, Requisition
from treasury.models import Alert, LedgerEntry, Payment

User = get_user_model()


class RequisitionToPaymentFlowTest(IntegrationTestBase):
    """
    Test complete E2E flow: Requisition → Approval → Payment → Ledger
    """

    def test_complete_requisition_approval_payment_flow(self):
        """
        Test the complete happy path:
        1. Staff creates requisition
        2. System resolves workflow (branch_manager → treasury)
        3. Branch manager approves
        4. Treasury approves
        5. Treasury executes payment
        6. Ledger entry is created
        7. Balances are updated correctly
        """
        # Step 1: Staff creates requisition
        initial_balance = self.treasury_fund.current_balance
        requisition_amount = Decimal("5000.00")

        requisition = self.create_requisition(
            requester=self.staff_user,
            amount=requisition_amount,
            purpose="Office supplies purchase",
            origin_type="branch",
        )

        # Verify requisition created
        self.assertEqual(requisition.status, "pending")
        self.assertEqual(requisition.requested_by, self.staff_user)
        self.assertEqual(requisition.amount, requisition_amount)

        # Step 2: Apply threshold and resolve workflow
        threshold = requisition.apply_threshold()
        self.assertEqual(threshold.name, "Tier 1")  # Should match tier1_threshold

        workflow = requisition.resolve_workflow()
        self.assertIsNotNone(workflow)
        self.assertEqual(len(workflow), 2)  # branch_manager + treasury

        # Verify first approver is branch_manager
        self.assertIsNotNone(requisition.next_approver)
        self.assertEqual(requisition.next_approver.role, "branch_manager")

        # Step 3: Branch manager approves
        manager_trail = self.approve_requisition(
            requisition=requisition,
            approver=self.branch_manager,
            notes="Approved by branch manager",
        )

        self.assertEqual(manager_trail.action, "approved")
        self.assertEqual(manager_trail.role, "branch_manager")

        # Verify workflow advanced to treasury
        requisition.refresh_from_db()
        self.assertIsNotNone(requisition.next_approver)
        self.assertEqual(requisition.next_approver.role, "treasury")

        # Step 4: Treasury approves
        treasury_trail = self.approve_requisition(
            requisition=requisition,
            approver=self.treasury_user,
            notes="Approved by treasury",
        )

        self.assertEqual(treasury_trail.action, "approved")

        # Verify workflow complete - status should be paid
        requisition.refresh_from_db()
        self.assertEqual(requisition.status, "paid")
        self.assertIsNone(requisition.next_approver)

        # Step 5: Treasury executes payment
        payment, ledger_entry = self.execute_payment(
            requisition=requisition, executor_user=self.treasury_user, method="mpesa"
        )

        # Verify payment created and completed
        self.assertEqual(payment.status, "success")
        self.assertEqual(payment.amount, requisition_amount)
        self.assertEqual(payment.requisition, requisition)
        self.assertEqual(payment.executor, self.treasury_user)
        self.assertIsNotNone(payment.execution_timestamp)
        self.assertTrue(payment.otp_verified)

        # Verify ledger entry created
        self.assertIsNotNone(ledger_entry)
        self.assertEqual(ledger_entry.entry_type, "debit")
        self.assertEqual(ledger_entry.amount, requisition_amount)

        # Verify fund balance updated
        self.treasury_fund.refresh_from_db()
        expected_balance = initial_balance - requisition_amount
        self.assertEqual(self.treasury_fund.current_balance, expected_balance)

        # Verify audit trail
        trails = ApprovalTrail.objects.filter(requisition=requisition)
        self.assertEqual(trails.count(), 2)
        self.assertTrue(all(t.action == "approved" for t in trails))

    def test_requisition_rejection_stops_workflow(self):
        """
        Test that rejecting a requisition stops the approval workflow
        """
        requisition = self.create_requisition(
            requester=self.staff_user,
            amount=Decimal("3000.00"),
            purpose="Rejected purchase",
        )

        # Apply threshold and resolve workflow
        requisition.apply_threshold()
        requisition.resolve_workflow()

        # Manager rejects
        trail = self.reject_requisition(
            requisition=requisition,
            approver=self.branch_manager,
            notes="Insufficient justification",
        )

        # Verify requisition rejected
        requisition.refresh_from_db()
        self.assertEqual(requisition.status, "rejected")
        self.assertIsNone(requisition.next_approver)

        # Verify rejection trail created
        self.assertEqual(trail.action, "rejected")
        self.assertEqual(trail.comment, "Insufficient justification")


class NoSelfApprovalTest(IntegrationTestBase):
    """
    Test that users cannot approve their own requisitions
    """

    def test_requester_cannot_self_approve(self):
        """
        Test that the person who created the requisition cannot approve it
        """
        # Branch manager creates their own requisition
        requisition = self.create_requisition(
            requester=self.branch_manager,
            amount=Decimal("2000.00"),
            purpose="Manager's own request",
        )

        # Apply threshold and resolve workflow
        requisition.apply_threshold()
        workflow = requisition.resolve_workflow()

        # Verify branch manager is NOT in the workflow (excluded due to self-approval rule)
        workflow_users = [item["user_id"] for item in workflow]
        self.assertNotIn(self.branch_manager.id, workflow_users)

        # Verify the requisition cannot be approved by the requester
        self.assertFalse(requisition.can_approve(self.branch_manager))

    def test_different_approver_succeeds(self):
        """
        Test that approval works when approver is different from requester
        """
        requisition = self.create_requisition(
            requester=self.staff_user,
            amount=Decimal("2000.00"),
            purpose="Staff request",
        )

        # Apply threshold and resolve workflow
        requisition.apply_threshold()
        requisition.resolve_workflow()

        # Verify branch manager CAN approve (different from requester)
        self.assertTrue(requisition.can_approve(self.branch_manager))

        # This should succeed
        trail = self.approve_requisition(
            requisition=requisition, approver=self.branch_manager
        )

        self.assertEqual(trail.action, "approved")
        self.assertNotEqual(requisition.requested_by, trail.user)


class UrgentFastTrackTest(IntegrationTestBase):
    """
    Test urgent requisition fast-track workflows
    """

    def test_urgent_requisition_skips_intermediate_approvers(self):
        """
        Test that urgent requisitions skip to final approver
        """
        requisition = self.create_requisition(
            requester=self.staff_user,
            amount=Decimal("8000.00"),
            purpose="Urgent medical supplies",
            is_urgent=True,
        )

        # Apply threshold (should be Tier 1 which allows fast-track)
        threshold = requisition.apply_threshold()
        self.assertTrue(threshold.allow_urgent_fasttrack)

        # Resolve workflow - should fast-track to final approver
        workflow = requisition.resolve_workflow()

        # Verify only one approver in workflow (final approver)
        self.assertEqual(len(workflow), 1)

        # Verify it's the final approver (treasury in Tier 1)
        final_approver = User.objects.get(id=workflow[0]["user_id"])
        self.assertEqual(final_approver.role, "treasury")

        # Verify marked as urgent
        self.assertTrue(requisition.is_urgent)

        # Treasury approves directly
        trail = self.approve_requisition(
            requisition=requisition,
            approver=final_approver,
            notes="Approved urgent request",
        )

        # Verify approved and workflow complete
        self.assertEqual(trail.action, "approved")
        requisition.refresh_from_db()
        self.assertEqual(requisition.status, "paid")


class PaymentFailureAndRetryTest(IntegrationTestBase):
    """
    Test payment failure scenarios and retry logic
    """

    def test_payment_failure_and_retry(self):
        """
        Test payment failure increments retry count and creates alerts
        """
        requisition = self.create_requisition(
            requester=self.staff_user,
            amount=Decimal("4000.00"),
            purpose="Test payment failure",
        )

        requisition.status = "paid"
        requisition.save()

        # Create payment
        payment = Payment.objects.create(
            requisition=requisition,
            amount=requisition.amount,
            method="mpesa",
            destination="+254700123456",
            status="pending",
        )

        # Simulate payment failure
        initial_retry_count = payment.retry_count
        payment.mark_failed("Gateway timeout")

        # Verify failure recorded
        payment.refresh_from_db()
        self.assertEqual(payment.status, "failed")
        self.assertEqual(payment.retry_count, initial_retry_count + 1)
        self.assertEqual(payment.last_error, "Gateway timeout")

        # Create alert for failed payment
        alert = Alert.objects.create(
            alert_type="payment_failed",
            severity="High",
            title=f"Payment Failed: {payment.payment_id}",
            message=f"Payment of {payment.amount} failed: {payment.last_error}",
            related_payment=payment,
        )

        self.assertEqual(alert.severity, "High")
        self.assertIsNotNone(alert.alert_id)

        # Simulate successful retry
        payment.status = "pending"
        payment.save()

        # Execute successfully
        payment.mark_executing()
        payment.mark_success(self.treasury_user)

        payment.refresh_from_db()
        self.assertEqual(payment.status, "success")
        self.assertGreater(payment.retry_count, 0)

    def test_max_retry_limit(self):
        """
        Test that payments track retry count properly
        """
        requisition = self.create_requisition(
            requester=self.staff_user,
            amount=Decimal("1000.00"),
            purpose="Test max retries",
        )

        payment = Payment.objects.create(
            requisition=requisition,
            amount=requisition.amount,
            method="bank",
            destination="123456789",
            status="pending",
            max_retries=3,
        )

        # Simulate multiple failures
        for i in range(payment.max_retries):
            payment.mark_failed(f"Failure attempt {i+1}")

        # Verify max retries reached
        payment.refresh_from_db()
        self.assertEqual(payment.retry_count, payment.max_retries)
        self.assertEqual(payment.status, "failed")


class PaymentExecutorSegregationTest(IntegrationTestBase):
    """
    Test that payment executor cannot be the requester (segregation of duties)
    """

    def test_requester_cannot_execute_payment(self):
        """
        Test that the person who requested cannot execute the payment
        """
        requisition = self.create_requisition(
            requester=self.treasury_user,  # Treasury user as requester
            amount=Decimal("5000.00"),
            purpose="Treasury request",
        )

        requisition.status = "paid"
        requisition.save()

        payment = Payment.objects.create(
            requisition=requisition,
            amount=requisition.amount,
            method="mpesa",
            destination="+254700999999",
            status="pending",
        )

        # Verify treasury user (requester) CANNOT execute their own payment
        self.assertFalse(payment.can_execute(self.treasury_user))

    def test_different_treasury_user_can_execute(self):
        """
        Test that a different treasury user can execute the payment
        """
        # Create another treasury user
        treasury_user_2 = self._create_user(
            username="treasury2@test.com",
            email="treasury2@test.com",
            role="treasury",
            company=self.company,
            is_centralized=True,
        )

        requisition = self.create_requisition(
            requester=self.staff_user,
            amount=Decimal("3000.00"),
            purpose="Staff request",
        )

        requisition.status = "paid"
        requisition.save()

        payment = Payment.objects.create(
            requisition=requisition,
            amount=requisition.amount,
            method="mpesa",
            destination="+254700888888",
            status="pending",
        )

        # Verify different treasury user CAN execute
        self.assertTrue(payment.can_execute(treasury_user_2))

        # Execute payment
        payment.mark_executing()
        payment.mark_success(treasury_user_2)

        payment.refresh_from_db()
        self.assertEqual(payment.status, "success")
        self.assertEqual(payment.executor, treasury_user_2)
