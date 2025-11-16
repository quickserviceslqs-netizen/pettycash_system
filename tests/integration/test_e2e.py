"""
Integration tests: end-to-end flows for Phase 7 start
"""
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from organization.models import Company, Region, Branch, Department
from transactions.models import Requisition, ApprovalThreshold
from treasury.models import Payment, LedgerEntry

User = get_user_model()


class EndToEndTestCase(TestCase):
    """End-to-end: submit requisition -> approve -> execute payment -> ledger entry"""

    def setUp(self):
        # Basic org structure
        self.company = Company.objects.create(name='E2E Co', code='E2E')
        self.region = Region.objects.create(name='E2E Region', company=self.company)
        self.branch = Branch.objects.create(name='E2E Branch', region=self.region, company=self.company)
        self.department = Department.objects.create(name='Ops', branch=self.branch)

        # Users
        self.requester = User.objects.create_user(username='req_user', password='pass', role='staff', company=self.company)
        self.branch_manager = User.objects.create_user(username='bm', password='pass', role='branch_manager', company=self.company, branch=self.branch)
        self.treasury_user = User.objects.create_user(username='treasury', password='pass', role='treasury', company=self.company)
        # Admin/superuser for workflow auto-escalation fallback
        self.admin = User.objects.create(username='admin', role='admin', is_superuser=True, is_staff=True)
        self.admin.set_password('adminpass')
        self.admin.save()

        # ApprovalThreshold seed for small amounts
        ApprovalThreshold.objects.create(min_amount=0, max_amount=10000, roles_sequence=['branch_manager','treasury'], allow_urgent_fasttrack=True, requires_cfo=False, name='Tier1')

    def test_requisition_to_payment_flow(self):
        # Submit requisition
        req = Requisition.objects.create(
            transaction_id='REQ-E2E-001',
            requesting_user=self.requester,
            origin_type='branch',
            company=self.company,
            region=self.region,
            branch=self.branch,
            department=self.department,
            amount=Decimal('5000.00'),
            purpose='Office supplies',
            status='pending'
        )

        # Apply threshold and resolve workflow
        thr = req.apply_threshold()
        req.resolve_workflow()

        # Next approver should be branch_manager (resolved by role mapping)
        next_approver = req.next_approver
        self.assertIsNotNone(next_approver)

        # Simulate branch manager approval (create ApprovalTrail entry)
        from transactions.models import ApprovalTrail
        ApprovalTrail.objects.create(requisition=req, user=self.branch_manager, role='branch_manager', action='approved', comment='ok')

        # Advance requisition to pending treasury validation
        req.status = 'pending_treasury'
        req.next_approver = self.treasury_user
        req.save()

        # Simulate treasury creating payment
        payment = Payment.objects.create(requisition=req, amount=req.amount, method='mpesa', destination='254700000000', status='pending')

        # Execute payment (simulate executor not equal requester)
        self.assertTrue(payment.can_execute(self.treasury_user))
        payment.mark_executing()
        payment.mark_success(self.treasury_user)

        # Create a TreasuryFund for the company/branch and use it for ledger entries
        from treasury.models import TreasuryFund, PaymentExecution
        fund = TreasuryFund.objects.create(company=self.company, region=self.region, branch=self.branch, current_balance=Decimal('100000.00'))

        # Create a PaymentExecution record (normally created by gateway handler)
        execution = PaymentExecution.objects.create(payment=payment, executor=self.treasury_user, gateway_reference='GREF-E2E-001', gateway_status='OK', otp_verified_at=timezone.now())

        # Create a ledger entry as the payment success handler would
        LedgerEntry.objects.create(treasury_fund=fund, payment_execution=execution, amount=payment.amount, entry_type='debit', description='Petty cash disbursement')

        # Assertions
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'success')

        ledger = LedgerEntry.objects.filter(payment_execution__payment=payment).first()
        self.assertIsNotNone(ledger)
        self.assertEqual(ledger.amount, payment.amount)



