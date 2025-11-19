"""
SQL Injection and Input Validation Security Tests
Phase 7: Security Testing

Tests protection against SQL injection, XSS, and other injection attacks.
"""

from django.test import TestCase, Client
from accounts.models import User
from organization.models import Company, Region, Branch
from transactions.models import Requisition
from decimal import Decimal
import json


class SQLInjectionTest(TestCase):
    """Test SQL injection prevention"""
    
    def setUp(self):
        """Create test data"""
        self.company = Company.objects.create(name='SQLi Test Corp', code='SQLI001')
        self.region = Region.objects.create(name='Test Region', code='REG001', company=self.company)
        self.branch = Branch.objects.create(name='Test Branch', code='BR001', region=self.region)
        
        self.user = User.objects.create_user(
            username='testuser',
            password='test123',
            email='test@test.com'
        )
        self.user.company = self.company
        self.user.branch = self.branch
        self.user.save()
        
        self.client = Client()
        self.client.login(username='testuser', password='test123')
    
    def test_sql_injection_in_search_parameter(self):
        """Search parameters should be sanitized against SQL injection"""
        # Common SQL injection payloads
        malicious_queries = [
            "' OR '1'='1",
            "'; DROP TABLE requisitions; --",
            "' UNION SELECT * FROM django_session--",
            "admin'--",
            "' OR 1=1--"
        ]
        
        for payload in malicious_queries:
            response = self.client.get(
                f'/api/requisitions/',
                {'search': payload}
            )
            
            # Should not return 500 error (indicates SQL error)
            self.assertNotEqual(response.status_code, 500,
                              f"SQL injection payload caused error: {payload}")
            
            # Should return safe response
            self.assertIn(response.status_code, [200, 400, 403])
    
    def test_sql_injection_in_transaction_id_lookup(self):
        """Transaction ID lookups should be parameterized"""
        malicious_ids = [
            "' OR '1'='1",
            "1'; DROP TABLE payments--",
            "1 UNION SELECT password FROM auth_user--"
        ]
        
        for payload in malicious_ids:
            response = self.client.get(f'/api/requisitions/{payload}/')
            
            # Should safely return 404, not cause SQL error
            self.assertIn(response.status_code, [404, 400],
                         f"SQL injection in ID lookup: {payload}")
    
    def test_sql_injection_in_filter_parameters(self):
        """Filter parameters should use ORM, not raw SQL"""
        response = self.client.get(
            '/api/requisitions/',
            {'status': "pending' OR '1'='1"}
        )
        
        # Should not cause error
        self.assertNotEqual(response.status_code, 500)
    
    def test_raw_sql_queries_use_parameters(self):
        """Any raw SQL should use parameterized queries"""
        # This would require code analysis to verify
        # For now, test that endpoints don't expose SQL errors
        
        # Try to cause SQL error with unusual input
        response = self.client.post(
            '/api/requisitions/',
            data=json.dumps({
                'transaction_id': "'; SELECT * FROM auth_user; --",
                'requested_by': "1' OR '1'='1",
                'origin_type': 'branch',
                'company': self.company.id,
                'branch': self.branch.id,
                'amount': '100.00',
                'purpose': 'SQL injection test'
            }),
            content_type='application/json'
        )
        
        # Should not return 500 (SQL error)
        self.assertNotEqual(response.status_code, 500)


class XSSPreventionTest(TestCase):
    """Test Cross-Site Scripting (XSS) prevention"""
    
    def setUp(self):
        """Create test data"""
        self.company = Company.objects.create(name='XSS Test Corp', code='XSS001')
        self.region = Region.objects.create(name='Test Region', code='REG001', company=self.company)
        self.branch = Branch.objects.create(name='Test Branch', code='BR001', region=self.region)
        
        self.user = User.objects.create_user(
            username='testuser',
            password='test123',
            email='test@test.com'
        )
        self.user.company = self.company
        self.user.branch = self.branch
        self.user.save()
        
        self.client = Client()
        self.client.login(username='testuser', password='test123')
    
    def test_xss_in_requisition_purpose(self):
        """Purpose field should sanitize script tags"""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>"
        ]
        
        for payload in xss_payloads:
            req = Requisition.objects.create(
                transaction_id=f'XSS-{hash(payload)}',
                requested_by=self.user,
                origin_type='branch',
                company=self.company,
                branch=self.branch,
                amount=Decimal('100.00'),
                purpose=payload,
                status='draft'
            )
            
            # Retrieve and verify sanitization
            response = self.client.get(f'/api/requisitions/{req.transaction_id}/')
            
            if response.status_code == 200:
                data = response.json()
                # Django templates should auto-escape
                # Verify raw script tag not in response
                response_text = str(data)
                self.assertNotIn('<script>', response_text.lower())
    
    def test_content_type_headers_prevent_xss(self):
        """API responses should have proper content-type headers"""
        response = self.client.get('/api/requisitions/')
        
        # Should be application/json, not text/html
        content_type = response.get('Content-Type', '')
        self.assertIn('application/json', content_type)
    
    def test_x_content_type_options_header(self):
        """Responses should include X-Content-Type-Options: nosniff"""
        response = self.client.get('/api/requisitions/')
        
        # Should have security header
        self.assertEqual(response.get('X-Content-Type-Options'), 'nosniff')


class InputValidationTest(TestCase):
    """Test input validation and sanitization"""
    
    def setUp(self):
        """Create test data"""
        self.company = Company.objects.create(name='Input Test Corp', code='INP001')
        self.region = Region.objects.create(name='Test Region', code='REG001', company=self.company)
        self.branch = Branch.objects.create(name='Test Branch', code='BR001', region=self.region)
        
        self.user = User.objects.create_user(
            username='testuser',
            password='test123',
            email='test@test.com'
        )
        self.user.company = self.company
        self.user.branch = self.branch
        self.user.save()
        
        self.client = Client()
        self.client.login(username='testuser', password='test123')
    
    def test_amount_field_rejects_negative_values(self):
        """Amount should not accept negative values"""
        response = self.client.post(
            '/api/requisitions/',
            data=json.dumps({
                'transaction_id': 'NEG-001',
                'requested_by': self.user.id,
                'origin_type': 'branch',
                'company': self.company.id,
                'branch': self.branch.id,
                'amount': '-100.00',
                'purpose': 'Negative amount test'
            }),
            content_type='application/json'
        )
        
        # Should be rejected
        self.assertIn(response.status_code, [400, 422])
    
    def test_amount_field_validates_decimal_format(self):
        """Amount should validate proper decimal format"""
        invalid_amounts = ['abc', '100.123', '1,000.00', '$100']
        
        for amount in invalid_amounts:
            response = self.client.post(
                '/api/requisitions/',
                data=json.dumps({
                    'transaction_id': f'DEC-{hash(amount)}',
                    'requested_by': self.user.id,
                    'origin_type': 'branch',
                    'company': self.company.id,
                    'branch': self.branch.id,
                    'amount': amount,
                    'purpose': 'Decimal validation test'
                }),
                content_type='application/json'
            )
            
            # Should be rejected
            self.assertIn(response.status_code, [400, 422],
                         f"Invalid amount accepted: {amount}")
    
    def test_required_fields_enforced(self):
        """Required fields should be validated"""
        response = self.client.post(
            '/api/requisitions/',
            data=json.dumps({
                'transaction_id': 'REQ-001',
                # Missing required fields
            }),
            content_type='application/json'
        )
        
        # Should be rejected
        self.assertEqual(response.status_code, 400)
    
    def test_field_max_length_enforced(self):
        """Fields should enforce maximum length"""
        very_long_purpose = 'A' * 10000  # Extremely long string
        
        response = self.client.post(
            '/api/requisitions/',
            data=json.dumps({
                'transaction_id': 'LEN-001',
                'requested_by': self.user.id,
                'origin_type': 'branch',
                'company': self.company.id,
                'branch': self.branch.id,
                'amount': '100.00',
                'purpose': very_long_purpose
            }),
            content_type='application/json'
        )
        
        # Should be rejected or truncated (depends on model definition)
        # At minimum, should not cause error
        self.assertNotEqual(response.status_code, 500)
    
    def test_enum_fields_validate_choices(self):
        """Enum fields should only accept valid choices"""
        response = self.client.post(
            '/api/requisitions/',
            data=json.dumps({
                'transaction_id': 'ENUM-001',
                'requested_by': self.user.id,
                'origin_type': 'invalid_origin_type',  # Invalid choice
                'company': self.company.id,
                'branch': self.branch.id,
                'amount': '100.00',
                'purpose': 'Enum validation test'
            }),
            content_type='application/json'
        )
        
        # Should be rejected
        self.assertIn(response.status_code, [400, 422])
