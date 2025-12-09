"""
Base test class and fixtures for integration testing
Provides common setup for E2E tests
"""

from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from organization.models import Branch, Company, Department, Region
from transactions.models import ApprovalTrail, Requisition
from treasury.models import Alert, LedgerEntry, Payment, TreasuryFund
from workflow.models import ApprovalThreshold

User = get_user_model()


class IntegrationTestBase(TransactionTestCase):
    """
    Base class for integration tests with full database rollback
    Uses TransactionTestCase for testing transaction behavior
    """

    def setUp(self):
        """Set up common test data for E2E scenarios"""
        # Create organizational structure
        self.company = Company.objects.create(name="Test Company Ltd", code="TC001")

        self.region = Region.objects.create(
            name="Central Region", code="CR001", company=self.company
        )

        self.branch = Branch.objects.create(
            name="Branch A", code="BA001", region=self.region
        )

        self.department = Department.objects.create(
            name="Operations", branch=self.branch
        )

        # Create treasury fund
        self.treasury_fund = TreasuryFund.objects.create(
            company=self.company,
            region=self.region,
            branch=self.branch,
            current_balance=Decimal("500000.00"),
            reorder_level=Decimal("50000.00"),
        )

        # Create approval thresholds
        self.tier1_threshold = ApprovalThreshold.objects.create(
            name="Tier 1",
            min_amount=Decimal("0.00"),
            max_amount=Decimal("10000.00"),
            roles_sequence=["branch_manager", "treasury"],
            allow_urgent_fasttrack=True,
            requires_cfo=False,
        )

        self.tier2_threshold = ApprovalThreshold.objects.create(
            name="Tier 2",
            min_amount=Decimal("10000.01"),
            max_amount=Decimal("50000.00"),
            roles_sequence=["branch_manager", "treasury", "cfo"],
            allow_urgent_fasttrack=True,
            requires_cfo=True,
        )

        # Create test users with different roles
        self.staff_user = self._create_user(
            username="staff@test.com",
            email="staff@test.com",
            role="staff",
            branch=self.branch,
            department=self.department,
        )

        self.branch_manager = self._create_user(
            username="manager@test.com",
            email="manager@test.com",
            role="branch_manager",
            branch=self.branch,
        )

        # Treasury user - set to branch to match workflow resolution
        # In production, workflow should check is_centralized_approver
        self.treasury_user = self._create_user(
            username="treasury@test.com",
            email="treasury@test.com",
            role="treasury",
            branch=self.branch,  # Set branch so workflow resolution finds them
            company=self.company,
            is_centralized=True,
        )

        self.cfo_user = self._create_user(
            username="cfo@test.com",
            email="cfo@test.com",
            role="cfo",
            company=self.company,
            is_centralized=True,
        )

        self.admin_user = self._create_user(
            username="admin@test.com",
            email="admin@test.com",
            role="admin",
            is_staff=True,
            is_superuser=True,
        )

    def _create_user(
        self,
        username,
        email,
        role,
        branch=None,
        department=None,
        region=None,
        company=None,
        is_staff=False,
        is_superuser=False,
        is_centralized=False,
    ):
        """Helper to create user with attributes"""
        # Resolve company and region from branch if not provided
        if branch and not region:
            region = branch.region
        if branch and not company:
            company = branch.region.company
        if region and not company:
            company = region.company
        if not company:
            company = self.company

        user = User.objects.create_user(
            username=username,
            email=email,
            password="testpass123",
            is_staff=is_staff,
            is_superuser=is_superuser,
            role=role,
            branch=branch,
            department=department,
            region=region,
            company=company,
            is_centralized_approver=is_centralized,
        )

        return user

    def create_requisition(
        self,
        requester,
        amount,
        purpose="Test requisition",
        origin_type="branch",
        is_urgent=False,
    ):
        """Helper to create a requisition"""
        requisition = Requisition.objects.create(
            requested_by=requester,
            amount=amount,
            purpose=purpose,
            origin_type=origin_type,
            is_urgent=is_urgent,
            status="pending",
            company=requester.company,
            region=requester.region,
            branch=requester.branch,
            department=requester.department,
        )
        return requisition

    def approve_requisition(self, requisition, approver, notes="Approved"):
        """Helper to approve a requisition and advance workflow"""
        # Verify approver can approve
        if not requisition.can_approve(approver):
            raise ValueError(f"{approver.username} cannot approve this requisition")

        # Create approval trail
        trail = ApprovalTrail.objects.create(
            requisition=requisition,
            user=approver,
            role=approver.role,
            action="approved",
            comment=notes,
            timestamp=timezone.now(),
        )

        # Advance workflow to next approver
        if requisition.workflow_sequence:
            current_idx = next(
                (
                    i
                    for i, item in enumerate(requisition.workflow_sequence)
                    if item["user_id"] == approver.id
                ),
                None,
            )

            if current_idx is not None and current_idx + 1 < len(
                requisition.workflow_sequence
            ):
                # More approvers needed
                next_item = requisition.workflow_sequence[current_idx + 1]
                requisition.next_approver = User.objects.get(id=next_item["user_id"])
                requisition.save(update_fields=["next_approver"])
            else:
                # Final approval - mark as paid status
                requisition.status = "paid"
                requisition.next_approver = None
                requisition.save(update_fields=["status", "next_approver"])

        return trail

    def reject_requisition(self, requisition, approver, notes="Rejected"):
        """Helper to reject a requisition"""
        # Verify approver can reject
        if not requisition.can_approve(approver):
            raise ValueError(f"{approver.username} cannot reject this requisition")

        # Create approval trail
        trail = ApprovalTrail.objects.create(
            requisition=requisition,
            user=approver,
            role=approver.role,
            action="rejected",
            comment=notes,
            timestamp=timezone.now(),
        )

        # Update requisition status
        requisition.status = "rejected"
        requisition.next_approver = None
        requisition.save(update_fields=["status", "next_approver"])

        return trail

    def execute_payment(self, requisition, executor_user, method="mpesa"):
        """Helper to execute payment for approved requisition"""
        payment = Payment.objects.create(
            requisition=requisition,
            amount=requisition.amount,
            method=method,
            destination=f"+254700{requisition.transaction_id[-6:]}",
            status="pending",
            otp_required=True,
        )

        # Verify executor can execute
        if not payment.can_execute(executor_user):
            raise ValueError(f"{executor_user.username} cannot execute this payment")

        # Simulate successful payment execution
        payment.mark_executing()
        payment.otp_verified = True
        payment.otp_verified_timestamp = timezone.now()
        payment.save()

        payment.mark_success(executor_user)

        # Update treasury fund balance
        balance_before = self.treasury_fund.current_balance
        self.treasury_fund.current_balance -= payment.amount
        self.treasury_fund.save()

        # Create ledger entry (simplified - in production this would be more complex)
        ledger_entry = LedgerEntry.objects.create(
            treasury_fund=self.treasury_fund,
            amount=payment.amount,
            entry_type="debit",
            description=f"Payment for requisition {requisition.transaction_id}",
            reconciled=False,
        )

        return payment, ledger_entry

    def tearDown(self):
        """Clean up after each test"""
        # TransactionTestCase handles rollback automatically
        pass
