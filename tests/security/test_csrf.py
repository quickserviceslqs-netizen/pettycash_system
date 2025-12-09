"""
Cross-Site Request Forgery (CSRF) Protection Tests
Phase 7: Security Testing

Tests CSRF token validation on all state-changing operations.
"""

import json
from decimal import Decimal

from django.test import Client, TestCase

from accounts.models import User
from organization.models import Branch, Company, Region
from transactions.models import Requisition


class CSRFProtectionTest(TestCase):
    """Test CSRF protection on POST/PUT/DELETE requests"""

    def setUp(self):
        """Create test data"""
        self.company = Company.objects.create(name="CSRF Test Corp", code="CSRF001")
        self.region = Region.objects.create(
            name="Test Region", code="REG001", company=self.company
        )
        self.branch = Branch.objects.create(
            name="Test Branch", code="BR001", region=self.region
        )

        self.user = User.objects.create_user(
            username="testuser", password="test123", email="test@test.com"
        )
        self.user.company = self.company
        self.user.branch = self.branch
        self.user.save()

        self.client = Client(enforce_csrf_checks=True)

    def test_post_without_csrf_token_fails(self):
        """POST requests without CSRF token should be rejected"""
        self.client.login(username="testuser", password="test123")

        payload = {
            "transaction_id": "CSRF-001",
            "requested_by": self.user.id,
            "origin_type": "branch",
            "company": self.company.id,
            "branch": self.branch.id,
            "amount": "100.00",
            "purpose": "CSRF test",
        }

        response = self.client.post(
            "/api/requisitions/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        # Should be rejected with 403 Forbidden
        self.assertEqual(response.status_code, 403)

    def test_post_with_valid_csrf_token_succeeds(self):
        """POST requests with valid CSRF token should succeed"""
        # Get CSRF token
        response = self.client.get("/api/csrf-token/")
        csrf_token = response.cookies.get("csrftoken")

        self.client.login(username="testuser", password="test123")

        payload = {
            "transaction_id": "CSRF-002",
            "requested_by": self.user.id,
            "origin_type": "branch",
            "company": self.company.id,
            "branch": self.branch.id,
            "amount": "100.00",
            "purpose": "CSRF valid test",
        }

        response = self.client.post(
            "/api/requisitions/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token.value if csrf_token else "",
        )

        # Should not be rejected for CSRF (may fail validation, but not 403)
        self.assertNotEqual(response.status_code, 403)

    def test_put_without_csrf_token_fails(self):
        """PUT requests without CSRF token should be rejected"""
        req = Requisition.objects.create(
            transaction_id="CSRF-003",
            requested_by=self.user,
            origin_type="branch",
            company=self.company,
            branch=self.branch,
            amount=Decimal("100.00"),
            purpose="CSRF PUT test",
            status="draft",
        )

        self.client.login(username="testuser", password="test123")

        response = self.client.put(
            f"/api/requisitions/{req.transaction_id}/",
            data=json.dumps({"purpose": "Updated purpose"}),
            content_type="application/json",
        )

        # Should be rejected
        self.assertEqual(response.status_code, 403)

    def test_delete_without_csrf_token_fails(self):
        """DELETE requests without CSRF token should be rejected"""
        req = Requisition.objects.create(
            transaction_id="CSRF-004",
            requested_by=self.user,
            origin_type="branch",
            company=self.company,
            branch=self.branch,
            amount=Decimal("100.00"),
            purpose="CSRF DELETE test",
            status="draft",
        )

        self.client.login(username="testuser", password="test123")

        response = self.client.delete(f"/api/requisitions/{req.transaction_id}/")

        # Should be rejected
        self.assertEqual(response.status_code, 403)

    def test_get_requests_not_affected_by_csrf(self):
        """GET requests should not require CSRF token"""
        self.client.login(username="testuser", password="test123")

        response = self.client.get("/api/requisitions/")

        # Should not be blocked by CSRF
        self.assertNotEqual(response.status_code, 403)

    def test_ajax_requests_use_header_csrf_token(self):
        """AJAX requests can provide CSRF token in X-CSRFToken header"""
        # Get CSRF token
        response = self.client.get("/api/csrf-token/")
        csrf_token = response.cookies.get("csrftoken")

        self.client.login(username="testuser", password="test123")

        payload = {
            "transaction_id": "CSRF-005",
            "requested_by": self.user.id,
            "origin_type": "branch",
            "company": self.company.id,
            "branch": self.branch.id,
            "amount": "100.00",
            "purpose": "AJAX CSRF test",
        }

        response = self.client.post(
            "/api/requisitions/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token.value if csrf_token else "",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        # Should not be rejected for CSRF
        self.assertNotEqual(response.status_code, 403)


class CSRFExemptAPITest(TestCase):
    """Test CSRF exemption for API endpoints that use token authentication"""

    def test_api_token_auth_exempt_from_csrf(self):
        """API endpoints using token authentication may be exempt from CSRF"""
        # This test depends on your API authentication strategy
        # If using DRF TokenAuthentication, CSRF may be exempted

        client = Client(enforce_csrf_checks=True)

        # Example: API call with token authentication
        response = client.get(
            "/api/requisitions/", HTTP_AUTHORIZATION="Token fake-token-123"
        )

        # Should not fail with CSRF error (may fail with auth error)
        self.assertNotEqual(
            response.status_code, 403, "Token-authenticated API should not require CSRF"
        )
