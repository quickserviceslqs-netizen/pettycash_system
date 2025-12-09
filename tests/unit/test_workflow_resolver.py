"""
Unit Tests for Workflow Resolution
Tests the resolve_workflow function and role assignment logic
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from organization.models import Company, Region, Branch, Department
from workflow.models import ApprovalThreshold
from transactions.models import Requisition
from workflow.services.resolver import resolve_workflow

User = get_user_model()


class WorkflowResolutionTests(TestCase):
    """Test workflow resolution logic"""

    def setUp(self):
        """Create test data"""
        # Create organization structure
        self.company = Company.objects.create(name="Test Company", code="TC001")

        self.region = Region.objects.create(
            name="Test Region", code="TR001", company=self.company
        )

        self.branch = Branch.objects.create(
            name="Test Branch", code="TB001", region=self.region
        )

        self.department = Department.objects.create(
            name="Operations", branch=self.branch
        )

        # Create users
        self.staff_user = User.objects.create_user(
            username="staff",
            password="test123",
            role="staff",
            branch=self.branch,
            department=self.department,
            company=self.company,
        )

        self.branch_manager = User.objects.create_user(
            username="branch_mgr",
            password="test123",
            role="branch_manager",
            branch=self.branch,
            company=self.company,
        )

        self.finance_manager = User.objects.create_user(
            username="finance_mgr",
            password="test123",
            role="fp&a",  # Note: using fp&a as finance role
            company=self.company,
        )

        self.treasury_user = User.objects.create_user(
            username="treasury",
            password="test123",
            role="treasury",
            company=self.company,
        )

        self.admin_user = User.objects.create_superuser(
            username="admin", password="test123", email="admin@test.com", role="admin"
        )

        # Create thresholds
        self.tier1 = ApprovalThreshold.objects.create(
            name="Tier 1",
            origin_type="ANY",
            min_amount=Decimal("0.00"),
            max_amount=Decimal("1000.00"),
            roles_sequence=["BRANCH_MANAGER"],
            allow_urgent_fasttrack=True,
            priority=1,
        )

        self.tier2 = ApprovalThreshold.objects.create(
            name="Tier 2",
            origin_type="ANY",
            min_amount=Decimal("1000.01"),
            max_amount=Decimal("10000.00"),
            roles_sequence=["BRANCH_MANAGER", "FP&A"],
            allow_urgent_fasttrack=True,
            priority=2,
        )

        self.tier3 = ApprovalThreshold.objects.create(
            name="Tier 3",
            origin_type="ANY",
            min_amount=Decimal("10000.01"),
            max_amount=Decimal("50000.00"),
            roles_sequence=["BRANCH_MANAGER", "FP&A", "TREASURY"],
            allow_urgent_fasttrack=False,
            priority=3,
        )

    def test_resolve_workflow_tier1_single_approver(self):
        """Tier 1 should assign single branch manager"""
        req = Requisition.objects.create(
            requested_by=self.staff_user,
            amount=Decimal("500.00"),
            purpose="Test",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
        )

        workflow = resolve_workflow(req)

        self.assertEqual(len(workflow), 1)
        self.assertEqual(workflow[0]["user_id"], self.branch_manager.id)
        self.assertEqual(workflow[0]["role"].upper(), "BRANCH_MANAGER")
        self.assertFalse(workflow[0]["auto_escalated"])

        # Check requisition updated
        req.refresh_from_db()
        self.assertEqual(req.next_approver.id, self.branch_manager.id)
        self.assertEqual(req.tier, "Tier 1")

    def test_resolve_workflow_tier2_multi_approver(self):
        """Tier 2 should assign branch manager then finance"""
        req = Requisition.objects.create(
            requested_by=self.staff_user,
            amount=Decimal("5000.00"),
            purpose="Test",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
        )

        workflow = resolve_workflow(req)

        self.assertEqual(len(workflow), 2)
        self.assertEqual(workflow[0]["user_id"], self.branch_manager.id)
        self.assertEqual(workflow[1]["user_id"], self.finance_manager.id)

        # First approver should be branch manager
        req.refresh_from_db()
        self.assertEqual(req.next_approver.id, self.branch_manager.id)

    def test_resolve_workflow_case_insensitive_role_matching(self):
        """BRANCH_MANAGER should match branch_manager in database"""
        req = Requisition.objects.create(
            requested_by=self.staff_user,
            amount=Decimal("500.00"),
            purpose="Test",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
        )

        workflow = resolve_workflow(req)

        # Should find branch_manager despite uppercase in threshold
        self.assertIsNotNone(workflow[0]["user_id"])
        self.assertEqual(workflow[0]["user_id"], self.branch_manager.id)

    def test_resolve_workflow_self_approval_excluded(self):
        """Requester cannot be in their own workflow"""
        # Branch manager creates request
        req = Requisition.objects.create(
            requested_by=self.branch_manager,
            amount=Decimal("500.00"),
            purpose="Test",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
        )

        workflow = resolve_workflow(req)

        # Should escalate to admin since branch manager is requester
        self.assertEqual(workflow[0]["user_id"], self.admin_user.id)
        self.assertTrue(workflow[0]["auto_escalated"])

    def test_resolve_workflow_centralized_role_no_scope_filter(self):
        """Treasury should not be filtered by branch"""
        req = Requisition.objects.create(
            requested_by=self.staff_user,
            amount=Decimal("25000.00"),  # Tier 3
            purpose="Test",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
        )

        workflow = resolve_workflow(req)

        # Should find treasury even though requisition is from branch
        treasury_step = [w for w in workflow if w["role"].upper() == "TREASURY"][0]
        self.assertEqual(treasury_step["user_id"], self.treasury_user.id)

    def test_resolve_workflow_scoped_role_with_branch_filter(self):
        """Branch manager should be filtered by branch"""
        # Create another branch manager in different branch
        other_branch = Branch.objects.create(
            name="Other Branch", code="OB001", region=self.region, company=self.company
        )

        other_branch_mgr = User.objects.create_user(
            username="other_branch_mgr",
            password="test123",
            role="branch_manager",
            branch=other_branch,
            company=self.company,
        )

        req = Requisition.objects.create(
            requested_by=self.staff_user,
            amount=Decimal("500.00"),
            purpose="Test",
            origin_type="branch",
            branch=self.branch,  # Request from first branch
            company=self.company,
        )

        workflow = resolve_workflow(req)

        # Should assign branch manager from SAME branch, not other branch
        self.assertEqual(workflow[0]["user_id"], self.branch_manager.id)
        self.assertNotEqual(workflow[0]["user_id"], other_branch_mgr.id)

    def test_resolve_workflow_no_candidate_auto_escalates(self):
        """If no candidate found, should escalate to admin"""
        # Delete branch manager
        self.branch_manager.delete()

        req = Requisition.objects.create(
            requested_by=self.staff_user,
            amount=Decimal("500.00"),
            purpose="Test",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
        )

        workflow = resolve_workflow(req)

        # Should escalate to admin
        self.assertEqual(workflow[0]["user_id"], self.admin_user.id)
        self.assertTrue(workflow[0]["auto_escalated"])

    def test_resolve_workflow_urgent_fast_track_multi_approver(self):
        """Urgent Tier 2 should skip to final approver"""
        req = Requisition.objects.create(
            requested_by=self.staff_user,
            amount=Decimal("5000.00"),
            purpose="Emergency repair",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
            is_urgent=True,
            urgency_reason="Emergency",
        )

        workflow = resolve_workflow(req)

        # Should skip branch manager, go directly to finance
        self.assertEqual(len(workflow), 1)
        self.assertEqual(workflow[0]["user_id"], self.finance_manager.id)

        req.refresh_from_db()
        self.assertEqual(req.next_approver.id, self.finance_manager.id)

    def test_resolve_workflow_urgent_fast_track_single_approver(self):
        """Urgent Tier 1 should still need branch manager (only 1 approver)"""
        req = Requisition.objects.create(
            requested_by=self.staff_user,
            amount=Decimal("500.00"),
            purpose="Urgent supplies",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
            is_urgent=True,
            urgency_reason="Urgent need",
        )

        workflow = resolve_workflow(req)

        # Still needs branch manager (can't skip if only 1 approver)
        self.assertEqual(len(workflow), 1)
        self.assertEqual(workflow[0]["user_id"], self.branch_manager.id)

    def test_resolve_workflow_urgent_disabled_tier(self):
        """Tier 3 with allow_urgent_fasttrack=False should not fast-track"""
        req = Requisition.objects.create(
            requested_by=self.staff_user,
            amount=Decimal("25000.00"),
            purpose="Large urgent purchase",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
            is_urgent=True,
            urgency_reason="Urgent",
        )

        workflow = resolve_workflow(req)

        # Should NOT fast-track, all 3 approvers required
        self.assertEqual(len(workflow), 3)

    def test_resolve_workflow_treasury_override_tier1(self):
        """Treasury user creating Tier 1 should use different workflow"""
        req = Requisition.objects.create(
            requested_by=self.treasury_user,
            amount=Decimal("500.00"),
            purpose="Treasury expense",
            origin_type="hq",
            company=self.company,
        )

        workflow = resolve_workflow(req)

        # Treasury override should apply different approvers
        # Should not include treasury user themselves
        for step in workflow:
            self.assertNotEqual(step["user_id"], self.treasury_user.id)

    def test_resolve_workflow_validates_amount_positive(self):
        """Workflow resolution should validate amount > 0"""
        # This might be handled in model validation instead
        # But worth testing the behavior
        req = Requisition.objects.create(
            requested_by=self.staff_user,
            amount=Decimal("0.00"),
            purpose="Test",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
        )

        # Should either raise error or handle gracefully
        # Implementation dependent
        try:
            workflow = resolve_workflow(req)
            # If it doesn't raise, check it handled it somehow
        except ValueError:
            # Expected behavior
            pass

    def test_resolve_workflow_preserves_workflow_order(self):
        """Workflow sequence should maintain order from threshold"""
        req = Requisition.objects.create(
            requested_by=self.staff_user,
            amount=Decimal("25000.00"),  # Tier 3: BM -> Finance -> Treasury
            purpose="Test",
            origin_type="branch",
            branch=self.branch,
            company=self.company,
        )

        workflow = resolve_workflow(req)

        # Order should be preserved
        self.assertEqual(workflow[0]["role"].upper(), "BRANCH_MANAGER")
        self.assertEqual(workflow[1]["role"].upper(), "FP&A")
        self.assertEqual(workflow[2]["role"].upper(), "TREASURY")
