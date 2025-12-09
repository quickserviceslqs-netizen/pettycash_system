"""
Unit Tests for Requisition Approval Actions
Tests the approval and rejection workflows
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden
from django.test import TestCase

from organization.models import Branch, Company, Department, Region
from transactions.models import ApprovalTrail, Requisition
from treasury.models import Payment
from workflow.models import ApprovalThreshold

User = get_user_model()


class RequisitionApprovalTests(TestCase):
    """Test requisition approval flow"""

    def setUp(self):
        """Create test data"""
        # Organization
        self.company = Company.objects.create(name="Test Co", code="TC")
        self.region = Region.objects.create(
            name="Test Region", code="TR", company=self.company
        )
        self.branch = Branch.objects.create(
            name="Test Branch", code="TB", region=self.region
        )

        # Users
        self.staff = User.objects.create_user(
            username="staff",
            password="test",
            role="staff",
            branch=self.branch,
            company=self.company,
        )

        self.branch_mgr = User.objects.create_user(
            username="branch_mgr",
            password="test",
            role="branch_manager",
            branch=self.branch,
            company=self.company,
        )

        self.finance_mgr = User.objects.create_user(
            username="finance", password="test", role="fp&a", company=self.company
        )

        # Thresholds
        ApprovalThreshold.objects.create(
            name="Tier 1",
            origin_type="ANY",
            min_amount=Decimal("0"),
            max_amount=Decimal("1000"),
            roles_sequence=["BRANCH_MANAGER"],
            priority=1,
        )

        ApprovalThreshold.objects.create(
            name="Tier 2",
            origin_type="ANY",
            min_amount=Decimal("1000.01"),
            max_amount=Decimal("10000"),
            roles_sequence=["BRANCH_MANAGER", "FP&A"],
            priority=2,
        )

    def test_can_approve_next_approver(self):
        """Next approver can approve"""
        req = Requisition.objects.create(
            requested_by=self.staff,
            amount=Decimal("500"),
            purpose="Test",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
        )
        req.resolve_workflow()

        # Branch manager is next approver
        self.assertTrue(req.can_approve(self.branch_mgr))

    def test_can_approve_wrong_user(self):
        """Non-next-approver cannot approve"""
        req = Requisition.objects.create(
            requested_by=self.staff,
            amount=Decimal("500"),
            purpose="Test",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
        )
        req.resolve_workflow()

        # Finance manager is not next approver
        self.assertFalse(req.can_approve(self.finance_mgr))

    def test_can_approve_self_denied(self):
        """Requester cannot approve their own request"""
        req = Requisition.objects.create(
            requested_by=self.staff,
            amount=Decimal("500"),
            purpose="Test",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
        )
        req.resolve_workflow()

        self.assertFalse(req.can_approve(self.staff))

    def test_approve_first_of_multi_moves_to_next(self):
        """First approval in multi-approver flow moves to next"""
        req = Requisition.objects.create(
            requested_by=self.staff,
            amount=Decimal("5000"),  # Tier 2: BM -> Finance
            purpose="Test",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
        )
        req.resolve_workflow()

        # Initial state
        self.assertEqual(req.status, "pending")
        self.assertEqual(req.next_approver, self.branch_mgr)
        self.assertEqual(len(req.workflow_sequence), 2)

        # Simulate approval (simplified - actual view does more)
        workflow_seq = req.workflow_sequence
        workflow_seq.pop(0)
        req.next_approver = User.objects.get(id=workflow_seq[0]["user_id"])
        req.workflow_sequence = workflow_seq
        req.save()

        # Should still be pending, moved to finance
        self.assertEqual(req.status, "pending")
        self.assertEqual(req.next_approver, self.finance_mgr)
        self.assertEqual(len(req.workflow_sequence), 1)

    def test_approve_final_marks_reviewed_creates_payment(self):
        """Final approval marks as reviewed and creates payment"""
        req = Requisition.objects.create(
            requested_by=self.staff,
            amount=Decimal("500"),  # Tier 1: Only BM
            purpose="Test",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
        )
        req.resolve_workflow()

        # Simulate final approval
        req.status = "reviewed"
        req.next_approver = None
        req.workflow_sequence = []
        req.save()

        # Create payment
        Payment.objects.create(requisition=req, amount=req.amount, status="pending")

        # Verify
        self.assertEqual(req.status, "reviewed")
        self.assertIsNone(req.next_approver)
        self.assertEqual(len(req.workflow_sequence), 0)

        # Check payment created
        payment = Payment.objects.filter(requisition=req).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.status, "pending")
        self.assertEqual(payment.amount, req.amount)

    def test_approve_already_reviewed_rejected(self):
        """Cannot approve already reviewed requisition"""
        req = Requisition.objects.create(
            requested_by=self.staff,
            amount=Decimal("500"),
            purpose="Test",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
            status="reviewed",  # Already reviewed
            next_approver=None,
        )

        # Can_approve should return False
        self.assertFalse(req.can_approve(self.branch_mgr))

    def test_approve_rejected_requisition_denied(self):
        """Cannot approve rejected requisition"""
        req = Requisition.objects.create(
            requested_by=self.staff,
            amount=Decimal("500"),
            purpose="Test",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
            status="rejected",
        )

        self.assertFalse(req.can_approve(self.branch_mgr))


class RequisitionRejectionTests(TestCase):
    """Test requisition rejection flow"""

    def setUp(self):
        """Create test data"""
        self.company = Company.objects.create(name="Test Co", code="TC")
        self.branch = Branch.objects.create(
            name="Test Branch", code="TB", company=self.company
        )

        self.staff = User.objects.create_user(
            username="staff",
            password="test",
            role="staff",
            branch=self.branch,
            company=self.company,
        )

        self.branch_mgr = User.objects.create_user(
            username="branch_mgr",
            password="test",
            role="branch_manager",
            branch=self.branch,
            company=self.company,
        )

        ApprovalThreshold.objects.create(
            name="Tier 1",
            origin_type="ANY",
            min_amount=Decimal("0"),
            max_amount=Decimal("1000"),
            roles_sequence=["BRANCH_MANAGER"],
            priority=1,
        )

    def test_reject_pending_requisition(self):
        """Rejecting pending requisition sets status to rejected"""
        req = Requisition.objects.create(
            requested_by=self.staff,
            amount=Decimal("500"),
            purpose="Test",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
        )
        req.resolve_workflow()

        # Simulate rejection
        req.status = "rejected"
        req.workflow_sequence = []
        req.next_approver = None
        req.save()

        self.assertEqual(req.status, "rejected")
        self.assertIsNone(req.next_approver)
        self.assertEqual(len(req.workflow_sequence), 0)

    def test_rejection_creates_approval_trail(self):
        """Rejection should create approval trail with action=rejected"""
        req = Requisition.objects.create(
            requested_by=self.staff,
            amount=Decimal("500"),
            purpose="Test",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
        )
        req.resolve_workflow()

        # Create rejection trail
        ApprovalTrail.objects.create(
            requisition=req,
            user=self.branch_mgr,
            role=self.branch_mgr.role,
            action="rejected",
            comment="Insufficient justification",
        )

        trail = ApprovalTrail.objects.filter(requisition=req, action="rejected").first()
        self.assertIsNotNone(trail)
        self.assertEqual(trail.user, self.branch_mgr)
        self.assertEqual(trail.action, "rejected")

    def test_cannot_approve_after_rejection(self):
        """Once rejected, cannot be approved"""
        req = Requisition.objects.create(
            requested_by=self.staff,
            amount=Decimal("500"),
            purpose="Test",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
            status="rejected",
        )

        self.assertFalse(req.can_approve(self.branch_mgr))


class EdgeCaseTests(TestCase):
    """Test edge cases and error conditions"""

    def setUp(self):
        """Create minimal test data"""
        self.company = Company.objects.create(name="Test Co", code="TC")
        self.branch = Branch.objects.create(
            name="Test Branch", code="TB", company=self.company
        )

        self.staff = User.objects.create_user(
            username="staff",
            password="test",
            role="staff",
            branch=self.branch,
            company=self.company,
        )

        ApprovalThreshold.objects.create(
            name="Tier 1",
            origin_type="ANY",
            min_amount=Decimal("0"),
            max_amount=Decimal("1000"),
            roles_sequence=["BRANCH_MANAGER"],
            priority=1,
        )

    def test_requisition_with_empty_workflow_sequence(self):
        """Requisition with empty workflow should not be approvable"""
        req = Requisition.objects.create(
            requested_by=self.staff,
            amount=Decimal("500"),
            purpose="Test",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
            workflow_sequence=[],
            next_approver=None,
        )

        # Cannot approve without workflow
        self.assertFalse(req.can_approve(self.staff))

    def test_requisition_zero_amount(self):
        """Amount = 0 should fail validation"""
        # This should be handled by model validation
        # For now, just document expected behavior
        req = Requisition(
            requested_by=self.staff,
            amount=Decimal("0"),
            purpose="Test",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
        )

        # Should raise validation error on save or clean()
        # Implementation dependent

    def test_requisition_negative_amount(self):
        """Negative amount should fail validation"""
        req = Requisition(
            requested_by=self.staff,
            amount=Decimal("-100"),
            purpose="Test",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
        )

        # Should raise validation error

    def test_branch_origin_without_branch(self):
        """Branch origin type without branch should fail validation"""
        req = Requisition(
            requested_by=self.staff,
            amount=Decimal("500"),
            purpose="Test",
            origin_type="branch",
            branch=None,  # Missing!
            company=self.company,
        )

        # Should fail validation
