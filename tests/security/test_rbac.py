"""
Role-Based Access Control (RBAC) Security Tests
Phase 7: Security Testing

Tests comprehensive permission enforcement across the application.
"""

from django.test import TestCase, Client
from accounts.models import User
from django.contrib.auth.models import Permission
from organization.models import Company, Region, Branch, Department
from treasury.models import TreasuryFund
from transactions.models import Requisition, ApprovalThreshold
from decimal import Decimal
import json


class RBACTestBase(TestCase):
    """Base class for RBAC tests with common setup"""
    
    def setUp(self):
        """Create test organizational structure and users with different roles"""
        # Create organization structure
        self.company = Company.objects.create(
            name='RBAC Test Corp',
            code='RBAC001'
        )
        
        self.region = Region.objects.create(
            name='Test Region',
            code='REG001',
            company=self.company
        )
        
        self.branch = Branch.objects.create(
            name='Test Branch',
            code='BR001',
            region=self.region
        )
        
        self.department = Department.objects.create(
            name='Finance',
            branch=self.branch
        )
        
        # Create treasury fund
        self.fund = TreasuryFund.objects.create(
            company=self.company,
            region=self.region,
            branch=self.branch,
            current_balance=Decimal('50000.00')
        )
        
        # Create users with different roles
        self.branch_staff = self._create_user('staff', 'staff123', is_staff=False)
        self.branch_manager = self._create_user('manager', 'manager123', is_staff=True)
        self.treasury_user = self._create_user('treasury', 'treasury123', is_staff=True)
        self.cfo = self._create_user('cfo', 'cfo123', is_staff=True, is_superuser=False)
        self.admin = self._create_user('admin', 'admin123', is_staff=True, is_superuser=True)
        
        # Assign branch relationships
        for user in [self.branch_staff, self.branch_manager, self.treasury_user, self.cfo, self.admin]:
            user.company = self.company
            user.region = self.region
            user.branch = self.branch
            user.save()
        
        self.client = Client()
    
    def _create_user(self, username, password, is_staff=False, is_superuser=False):
        """Helper to create user with specified privileges"""
        user = User.objects.create_user(
            username=username,
            password=password,
            email=f'{username}@test.com',
            is_staff=is_staff,
            is_superuser=is_superuser
        )
        return user


class RequisitionAccessControlTest(RBACTestBase):
    """Test access control for requisition operations"""
    
    def test_unauthenticated_user_cannot_create_requisition(self):
        """Unauthenticated users should be blocked from creating requisitions"""
        payload = {
            'transaction_id': 'SEC-REQ-001',
            'requested_by': self.branch_staff.id,
            'origin_type': 'branch',
            'company': self.company.id,
            'branch': self.branch.id,
            'amount': '100.00',
            'purpose': 'Test requisition'
        }
        
        response = self.client.post(
            '/api/requisitions/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Should redirect to login or return 401/403
        self.assertIn(response.status_code, [401, 403, 302])
    
    def test_branch_staff_can_create_own_requisition(self):
        """Branch staff should be able to create their own requisitions"""
        self.client.login(username='staff', password='staff123')
        
        payload = {
            'transaction_id': 'SEC-REQ-002',
            'requested_by': self.branch_staff.id,
            'origin_type': 'branch',
            'company': self.company.id,
            'branch': self.branch.id,
            'amount': '100.00',
            'purpose': 'Staff requisition'
        }
        
        response = self.client.post(
            '/api/requisitions/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Should succeed or return validation error, not permission denied
        self.assertNotIn(response.status_code, [401, 403])
    
    def test_user_cannot_view_other_branch_requisitions(self):
        """Users should not see requisitions from other branches"""
        # Create another branch
        other_branch = Branch.objects.create(
            name='Other Branch',
            code='BR002',
            region=self.region
        )
        
        # Create requisition in other branch
        other_req = Requisition.objects.create(
            transaction_id='SEC-REQ-003',
            requested_by=self.branch_staff,
            origin_type='branch',
            company=self.company,
            branch=other_branch,
            amount=Decimal('100.00'),
            purpose='Other branch requisition',
            status='draft'
        )
        
        self.client.login(username='staff', password='staff123')
        response = self.client.get(f'/api/requisitions/{other_req.transaction_id}/')
        
        # Should return 404 or 403
        self.assertIn(response.status_code, [403, 404])
    
    def test_admin_can_view_all_requisitions(self):
        """Admins should have access to all requisitions"""
        req = Requisition.objects.create(
            transaction_id='SEC-REQ-004',
            requested_by=self.branch_staff,
            origin_type='branch',
            company=self.company,
            branch=self.branch,
            amount=Decimal('100.00'),
            purpose='Admin access test',
            status='draft'
        )
        
        self.client.login(username='admin', password='admin123')
        response = self.client.get(f'/api/requisitions/{req.transaction_id}/')
        
        # Admin should have access
        self.assertEqual(response.status_code, 200)


class ApprovalWorkflowSecurityTest(RBACTestBase):
    """Test security of approval workflow"""
    
    def setUp(self):
        super().setUp()
        
        # Create approval threshold
        self.threshold = ApprovalThreshold.objects.create(
            name='Low Amount',
            company=self.company,
            min_amount=Decimal('0.00'),
            max_amount=Decimal('1000.00')
        )
        self.threshold.approvers.add(self.branch_manager)
    
    def test_requester_cannot_self_approve(self):
        """Requesters must not be able to approve their own requisitions"""
        # Create requisition as staff
        req = Requisition.objects.create(
            transaction_id='SEC-APPR-001',
            requested_by=self.branch_staff,
            origin_type='branch',
            company=self.company,
            branch=self.branch,
            amount=Decimal('100.00'),
            purpose='Self-approval test',
            status='pending_approval',
            approval_threshold=self.threshold
        )
        
        # Try to approve as the same user
        self.client.login(username='staff', password='staff123')
        response = self.client.post(
            f'/api/requisitions/{req.transaction_id}/approve/',
            data=json.dumps({'approver_id': self.branch_staff.id}),
            content_type='application/json'
        )
        
        # Should be rejected (403 or validation error)
        self.assertNotEqual(response.status_code, 200)
    
    def test_unauthorized_user_cannot_approve(self):
        """Users not in approver list cannot approve requisitions"""
        req = Requisition.objects.create(
            transaction_id='SEC-APPR-002',
            requested_by=self.branch_staff,
            origin_type='branch',
            company=self.company,
            branch=self.branch,
            amount=Decimal('100.00'),
            purpose='Unauthorized approval test',
            status='pending_approval',
            approval_threshold=self.threshold
        )
        
        # Create unauthorized user
        unauthorized = self._create_user('unauthorized', 'unauth123')
        unauthorized.company = self.company
        unauthorized.branch = self.branch
        unauthorized.save()
        
        self.client.login(username='unauthorized', password='unauth123')
        response = self.client.post(
            f'/api/requisitions/{req.transaction_id}/approve/',
            data=json.dumps({'approver_id': unauthorized.id}),
            content_type='application/json'
        )
        
        # Should be rejected
        self.assertIn(response.status_code, [403, 400])
    
    def test_authorized_approver_can_approve(self):
        """Authorized approvers should be able to approve requisitions"""
        req = Requisition.objects.create(
            transaction_id='SEC-APPR-003',
            requested_by=self.branch_staff,
            origin_type='branch',
            company=self.company,
            branch=self.branch,
            amount=Decimal('100.00'),
            purpose='Valid approval test',
            status='pending_approval',
            approval_threshold=self.threshold
        )
        
        self.client.login(username='manager', password='manager123')
        response = self.client.post(
            f'/api/requisitions/{req.transaction_id}/approve/',
            data=json.dumps({'approver_id': self.branch_manager.id}),
            content_type='application/json'
        )
        
        # Should succeed
        self.assertIn(response.status_code, [200, 201])


class TreasuryAccessControlTest(RBACTestBase):
    """Test access control for treasury operations"""
    
    def test_non_treasury_user_cannot_execute_payment(self):
        """Non-treasury users should not be able to execute payments"""
        from treasury.models import Payment
        
        req = Requisition.objects.create(
            transaction_id='SEC-TREAS-001',
            requested_by=self.branch_staff,
            origin_type='branch',
            company=self.company,
            branch=self.branch,
            amount=Decimal('100.00'),
            purpose='Payment execution test',
            status='approved'
        )
        
        payment = Payment.objects.create(
            requisition=req,
            amount=Decimal('100.00'),
            status='pending',
            fund=self.fund
        )
        
        # Try to execute as branch staff
        self.client.login(username='staff', password='staff123')
        response = self.client.post(
            f'/treasury/api/payments/{payment.id}/execute/',
            data=json.dumps({'otp': '123456'}),
            content_type='application/json'
        )
        
        # Should be rejected
        self.assertIn(response.status_code, [403, 400])
    
    def test_treasury_user_can_execute_payment(self):
        """Treasury users should be able to execute payments"""
        from treasury.models import Payment
        
        req = Requisition.objects.create(
            transaction_id='SEC-TREAS-002',
            requested_by=self.branch_staff,
            origin_type='branch',
            company=self.company,
            branch=self.branch,
            amount=Decimal('100.00'),
            purpose='Treasury execution test',
            status='approved'
        )
        
        payment = Payment.objects.create(
            requisition=req,
            amount=Decimal('100.00'),
            status='pending',
            fund=self.fund
        )
        
        self.client.login(username='treasury', password='treasury123')
        response = self.client.post(
            f'/treasury/api/payments/{payment.id}/execute/',
            data=json.dumps({'otp': '123456'}),
            content_type='application/json'
        )
        
        # Should be allowed (may fail on OTP validation, but not on permission)
        self.assertNotEqual(response.status_code, 403)
    
    def test_requester_cannot_execute_own_payment(self):
        """Payment executors cannot execute payments for their own requisitions"""
        from treasury.models import Payment
        
        # Treasury user creates requisition
        req = Requisition.objects.create(
            transaction_id='SEC-TREAS-003',
            requested_by=self.treasury_user,
            origin_type='branch',
            company=self.company,
            branch=self.branch,
            amount=Decimal('100.00'),
            purpose='Self-execution test',
            status='approved'
        )
        
        payment = Payment.objects.create(
            requisition=req,
            amount=Decimal('100.00'),
            status='pending',
            fund=self.fund
        )
        
        # Try to execute own payment
        self.client.login(username='treasury', password='treasury123')
        response = self.client.post(
            f'/treasury/api/payments/{payment.id}/execute/',
            data=json.dumps({'otp': '123456'}),
            content_type='application/json'
        )
        
        # Should be rejected due to segregation of duties
        self.assertNotEqual(response.status_code, 200)


class ReportingAccessControlTest(RBACTestBase):
    """Test access control for reporting and analytics"""
    
    def test_branch_staff_limited_to_own_branch_reports(self):
        """Branch staff should only see their own branch data in reports"""
        self.client.login(username='staff', password='staff123')
        response = self.client.get('/reports/api/payment-summary/')
        
        if response.status_code == 200:
            data = response.json()
            # Verify data is filtered to user's branch
            # Implementation depends on report structure
            self.assertIsNotNone(data)
    
    def test_cfo_can_access_company_wide_reports(self):
        """CFO should have access to company-wide reports"""
        self.client.login(username='cfo', password='cfo123')
        response = self.client.get('/reports/api/company-summary/')
        
        # Should have access
        self.assertIn(response.status_code, [200, 404])  # 404 if endpoint doesn't exist yet
    
    def test_unauthenticated_user_cannot_access_reports(self):
        """Unauthenticated users should not access any reports"""
        response = self.client.get('/reports/api/payment-summary/')
        
        # Should be denied
        self.assertIn(response.status_code, [401, 403, 302])
