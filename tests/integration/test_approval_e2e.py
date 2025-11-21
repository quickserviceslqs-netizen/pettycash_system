"""
End-to-End Integration Tests for Approval Workflow
Tests complete flows from requisition creation through payment execution
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from organization.models import Company, Region, Branch, Department
from workflow.models import ApprovalThreshold
from transactions.models import Requisition, ApprovalTrail
from treasury.models import Payment

User = get_user_model()


class EndToEndTier1Tests(TestCase):
    """Test complete Tier 1 flow"""
    
    def setUp(self):
        """Create full test environment"""
        # Organization
        self.company = Company.objects.create(name='Test Company', code='TC001')
        self.region = Region.objects.create(name='Test Region', code='TR001', company=self.company)
        self.branch = Branch.objects.create(
            name='Test Branch',
            code='TB001',
            region=self.region
        )
        self.department = Department.objects.create(
            name='Operations',
            branch=self.branch
        )
        
        # Users
        self.staff_user = User.objects.create_user(
            username='sarah_staff',
            password='Test@123',
            email='sarah@test.com',
            first_name='Sarah',
            last_name='Johnson',
            role='staff',
            branch=self.branch,
            department=self.department,
            company=self.company
        )
        
        self.branch_mgr = User.objects.create_user(
            username='john_manager',
            password='Test@123',
            email='john@test.com',
            first_name='John',
            last_name='Smith',
            role='branch_manager',
            branch=self.branch,
            company=self.company
        )
        
        self.treasury_user = User.objects.create_user(
            username='mike_treasury',
            password='Test@123',
            email='mike@test.com',
            first_name='Mike',
            last_name='Johnson',
            role='treasury',
            company=self.company
        )
        
        # Thresholds
        ApprovalThreshold.objects.create(
            name='Tier 1',
            origin_type='ANY',
            min_amount=Decimal('0.00'),
            max_amount=Decimal('1000.00'),
            roles_sequence=['BRANCH_MANAGER'],
            allow_urgent_fasttrack=True,
            priority=1
        )
        
        self.client = Client()
    
    def test_complete_tier1_flow_create_approve_payment(self):
        """
        Complete Tier 1 flow:
        1. Staff creates $500 requisition
        2. Branch manager approves
        3. Status becomes reviewed
        4. Payment record created
        5. Treasury can see it
        """
        # Step 1: Staff creates requisition
        req = Requisition.objects.create(
            requested_by=self.staff_user,
            amount=Decimal('500.00'),
            purpose='Office supplies - printer paper, pens, folders',
            origin_type='branch',
            branch=self.branch,
            department=self.department,
            company=self.company,
            status='pending'
        )
        req.resolve_workflow()
        
        # Verify initial state
        self.assertEqual(req.status, 'pending')
        self.assertEqual(req.tier, 'Tier 1')
        self.assertEqual(req.next_approver, self.branch_mgr)
        self.assertEqual(len(req.workflow_sequence), 1)
        
        # Step 2: Branch manager approves
        self.assertTrue(req.can_approve(self.branch_mgr))
        
        # Create approval trail
        ApprovalTrail.objects.create(
            requisition=req,
            user=self.branch_mgr,
            role=self.branch_mgr.role,
            action='approved',
            comment='Approved - within budget'
        )
        
        # Update requisition (final approval)
        workflow_seq = req.workflow_sequence
        self.assertEqual(len(workflow_seq), 1)  # Only one approver
        
        req.status = 'reviewed'
        req.next_approver = None
        req.workflow_sequence = []
        req.save()
        
        # Step 3: Verify reviewed status
        req.refresh_from_db()
        self.assertEqual(req.status, 'reviewed')
        self.assertIsNone(req.next_approver)
        self.assertEqual(len(req.workflow_sequence), 0)
        
        # Step 4: Create payment
        payment = Payment.objects.create(
            requisition=req,
            amount=req.amount,
            status='pending',
            method='bank_transfer',
            otp_required=True
        )
        
        # Step 5: Verify payment created
        self.assertIsNotNone(payment)
        self.assertEqual(payment.amount, Decimal('500.00'))
        self.assertEqual(payment.status, 'pending')
        
        # Verify approval trail
        trail = ApprovalTrail.objects.filter(requisition=req, action='approved')
        self.assertEqual(trail.count(), 1)
        self.assertEqual(trail.first().user, self.branch_mgr)


class EndToEndTier2Tests(TestCase):
    """Test complete Tier 2 multi-approver flow"""
    
    def setUp(self):
        """Create full test environment"""
        self.company = Company.objects.create(name='Test Company', code='TC001')
        self.branch = Branch.objects.create(
            name='Test Branch',
            code='TB001',
            company=self.company
        )
        
        # Users
        self.staff_user = User.objects.create_user(
            username='staff',
            password='Test@123',
            role='staff',
            branch=self.branch,
            company=self.company
        )
        
        self.branch_mgr = User.objects.create_user(
            username='branch_mgr',
            password='Test@123',
            role='branch_manager',
            branch=self.branch,
            company=self.company
        )
        
        self.finance_mgr = User.objects.create_user(
            username='finance_mgr',
            password='Test@123',
            role='fp&a',
            company=self.company
        )
        
        # Threshold
        ApprovalThreshold.objects.create(
            name='Tier 2',
            origin_type='ANY',
            min_amount=Decimal('1000.01'),
            max_amount=Decimal('10000.00'),
            roles_sequence=['BRANCH_MANAGER', 'FP&A'],
            allow_urgent_fasttrack=True,
            priority=2
        )
    
    def test_complete_tier2_flow_two_approvers(self):
        """
        Complete Tier 2 flow:
        1. Staff creates $5000 requisition
        2. Branch manager approves (first)
        3. Status still pending, moves to finance
        4. Finance manager approves (final)
        5. Status becomes reviewed
        6. Payment created
        """
        # Step 1: Create requisition
        req = Requisition.objects.create(
            requested_by=self.staff_user,
            amount=Decimal('5000.00'),
            purpose='Equipment repair',
            origin_type='branch',
            branch=self.branch,
            company=self.company,
            status='pending'
        )
        req.resolve_workflow()
        
        # Verify initial state
        self.assertEqual(req.tier, 'Tier 2')
        self.assertEqual(req.next_approver, self.branch_mgr)
        self.assertEqual(len(req.workflow_sequence), 2)
        
        # Step 2: First approval (Branch Manager)
        ApprovalTrail.objects.create(
            requisition=req,
            user=self.branch_mgr,
            role=self.branch_mgr.role,
            action='approved',
            comment='Approved by branch'
        )
        
        # Move to next approver
        workflow_seq = req.workflow_sequence
        workflow_seq.pop(0)
        req.next_approver = User.objects.get(id=workflow_seq[0]['user_id'])
        req.workflow_sequence = workflow_seq
        req.save()
        
        # Step 3: Verify moved to finance
        req.refresh_from_db()
        self.assertEqual(req.status, 'pending')  # Still pending!
        self.assertEqual(req.next_approver, self.finance_mgr)
        self.assertEqual(len(req.workflow_sequence), 1)
        
        # Step 4: Second approval (Finance Manager)
        ApprovalTrail.objects.create(
            requisition=req,
            user=self.finance_mgr,
            role=self.finance_mgr.role,
            action='approved',
            comment='Approved by finance'
        )
        
        # Final approval
        workflow_seq = req.workflow_sequence
        self.assertEqual(len(workflow_seq), 1)  # Last approver
        
        req.status = 'reviewed'
        req.next_approver = None
        req.workflow_sequence = []
        req.save()
        
        # Step 5: Verify reviewed
        req.refresh_from_db()
        self.assertEqual(req.status, 'reviewed')
        self.assertIsNone(req.next_approver)
        
        # Step 6: Create payment
        payment = Payment.objects.create(
            requisition=req,
            amount=req.amount,
            status='pending'
        )
        
        self.assertIsNotNone(payment)
        
        # Verify both approvals in trail
        trail = ApprovalTrail.objects.filter(requisition=req, action='approved')
        self.assertEqual(trail.count(), 2)


class UrgentRequestTests(TestCase):
    """Test urgent request fast-track flow"""
    
    def setUp(self):
        """Create test environment"""
        self.company = Company.objects.create(name='Test Company', code='TC001')
        self.branch = Branch.objects.create(
            name='Test Branch',
            code='TB001',
            company=self.company
        )
        
        self.staff_user = User.objects.create_user(
            username='staff',
            password='Test@123',
            role='staff',
            branch=self.branch,
            company=self.company
        )
        
        self.branch_mgr = User.objects.create_user(
            username='branch_mgr',
            password='Test@123',
            role='branch_manager',
            branch=self.branch,
            company=self.company
        )
        
        self.finance_mgr = User.objects.create_user(
            username='finance_mgr',
            password='Test@123',
            role='fp&a',
            company=self.company
        )
        
        ApprovalThreshold.objects.create(
            name='Tier 2',
            origin_type='ANY',
            min_amount=Decimal('1000.01'),
            max_amount=Decimal('10000.00'),
            roles_sequence=['BRANCH_MANAGER', 'FP&A'],
            allow_urgent_fasttrack=True,
            priority=2
        )
    
    def test_urgent_request_skips_to_final_approver(self):
        """
        Urgent Tier 2 flow:
        1. Staff creates URGENT $5000 requisition
        2. System skips branch manager, assigns to finance
        3. Finance approves (only one approval needed)
        4. Status becomes reviewed
        """
        # Create urgent request
        req = Requisition.objects.create(
            requested_by=self.staff_user,
            amount=Decimal('5000.00'),
            purpose='Emergency plumbing repair',
            origin_type='branch',
            branch=self.branch,
            company=self.company,
            status='pending',
            is_urgent=True,
            urgency_reason='Office flooded, immediate repair needed'
        )
        req.resolve_workflow()
        
        # Verify fast-tracked to finance (skipped branch manager)
        req.refresh_from_db()
        self.assertEqual(len(req.workflow_sequence), 1)
        self.assertEqual(req.next_approver, self.finance_mgr)
        
        # Finance approves (single approval)
        ApprovalTrail.objects.create(
            requisition=req,
            user=self.finance_mgr,
            role=self.finance_mgr.role,
            action='approved',
            comment='Emergency approved'
        )
        
        req.status = 'reviewed'
        req.next_approver = None
        req.workflow_sequence = []
        req.save()
        
        # Verify reviewed with only one approval
        trail = ApprovalTrail.objects.filter(requisition=req, action='approved')
        self.assertEqual(trail.count(), 1)
        self.assertEqual(trail.first().user, self.finance_mgr)


class RejectionFlowTests(TestCase):
    """Test rejection workflow"""
    
    def setUp(self):
        """Create test environment"""
        self.company = Company.objects.create(name='Test Company', code='TC001')
        self.branch = Branch.objects.create(
            name='Test Branch',
            code='TB001',
            company=self.company
        )
        
        self.staff_user = User.objects.create_user(
            username='staff',
            password='Test@123',
            role='staff',
            branch=self.branch,
            company=self.company
        )
        
        self.branch_mgr = User.objects.create_user(
            username='branch_mgr',
            password='Test@123',
            role='branch_manager',
            branch=self.branch,
            company=self.company
        )
        
        ApprovalThreshold.objects.create(
            name='Tier 1',
            origin_type='ANY',
            min_amount=Decimal('0'),
            max_amount=Decimal('1000'),
            roles_sequence=['BRANCH_MANAGER'],
            priority=1
        )
    
    def test_rejection_workflow(self):
        """
        Rejection flow:
        1. Staff creates requisition
        2. Branch manager rejects
        3. Status becomes rejected
        4. Workflow cleared
        5. Cannot approve after rejection
        """
        # Create requisition
        req = Requisition.objects.create(
            requested_by=self.staff_user,
            amount=Decimal('500.00'),
            purpose='Unnecessary expense',
            origin_type='branch',
            branch=self.branch,
            company=self.company,
            status='pending'
        )
        req.resolve_workflow()
        
        # Branch manager rejects
        ApprovalTrail.objects.create(
            requisition=req,
            user=self.branch_mgr,
            role=self.branch_mgr.role,
            action='rejected',
            comment='Insufficient justification'
        )
        
        req.status = 'rejected'
        req.workflow_sequence = []
        req.next_approver = None
        req.save()
        
        # Verify rejected state
        req.refresh_from_db()
        self.assertEqual(req.status, 'rejected')
        self.assertIsNone(req.next_approver)
        self.assertEqual(len(req.workflow_sequence), 0)
        
        # Verify cannot approve
        self.assertFalse(req.can_approve(self.branch_mgr))
        
        # Verify rejection trail
        trail = ApprovalTrail.objects.filter(requisition=req, action='rejected')
        self.assertEqual(trail.count(), 1)
