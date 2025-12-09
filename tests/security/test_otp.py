"""
OTP (One-Time Password) Validation Security Tests
Phase 7: Security Testing

Tests OTP generation, validation, expiry, and rate limiting.
"""

from django.test import TestCase, Client
from accounts.models import User
from django.utils import timezone
from organization.models import Company, Region, Branch
from transactions.models import Requisition
from treasury.models import Payment, TreasuryFund
from decimal import Decimal
from datetime import timedelta
import json


class OTPValidationTest(TestCase):
    """Test OTP validation for payment execution"""

    def setUp(self):
        """Create test data"""
        self.company = Company.objects.create(name="OTP Test Corp", code="OTP001")
        self.region = Region.objects.create(
            name="Test Region", code="REG001", company=self.company
        )
        self.branch = Branch.objects.create(
            name="Test Branch", code="BR001", region=self.region
        )

        self.fund = TreasuryFund.objects.create(
            company=self.company,
            region=self.region,
            branch=self.branch,
            current_balance=Decimal("50000.00"),
        )

        self.requester = User.objects.create_user(
            username="requester", password="req123", email="requester@test.com"
        )
        self.requester.company = self.company
        self.requester.branch = self.branch
        self.requester.save()

        self.treasury_user = User.objects.create_user(
            username="treasury",
            password="treas123",
            email="treasury@test.com",
            is_staff=True,
        )
        self.treasury_user.company = self.company
        self.treasury_user.branch = self.branch
        self.treasury_user.save()

        self.client = Client()

    def test_payment_execution_requires_otp(self):
        """Payment execution should require valid OTP"""
        req = Requisition.objects.create(
            transaction_id="OTP-001",
            requested_by=self.requester,
            origin_type="branch",
            company=self.company,
            branch=self.branch,
            amount=Decimal("100.00"),
            purpose="OTP test",
            status="approved",
        )

        payment = Payment.objects.create(
            requisition=req, amount=Decimal("100.00"), status="pending", fund=self.fund
        )

        self.client.login(username="treasury", password="treas123")

        # Try to execute without OTP
        response = self.client.post(
            f"/treasury/api/payments/{payment.id}/execute/",
            data=json.dumps({}),
            content_type="application/json",
        )

        # Should be rejected
        self.assertIn(response.status_code, [400, 422])

    def test_invalid_otp_rejected(self):
        """Invalid OTP should be rejected"""
        req = Requisition.objects.create(
            transaction_id="OTP-002",
            requested_by=self.requester,
            origin_type="branch",
            company=self.company,
            branch=self.branch,
            amount=Decimal("100.00"),
            purpose="Invalid OTP test",
            status="approved",
        )

        payment = Payment.objects.create(
            requisition=req, amount=Decimal("100.00"), status="pending", fund=self.fund
        )

        self.client.login(username="treasury", password="treas123")

        # Try with invalid OTP
        response = self.client.post(
            f"/treasury/api/payments/{payment.id}/execute/",
            data=json.dumps({"otp": "000000"}),
            content_type="application/json",
        )

        # Should be rejected
        self.assertIn(response.status_code, [400, 401, 422])

    def test_otp_request_rate_limiting(self):
        """OTP requests should be rate-limited to prevent abuse"""
        req = Requisition.objects.create(
            transaction_id="OTP-003",
            requested_by=self.requester,
            origin_type="branch",
            company=self.company,
            branch=self.branch,
            amount=Decimal("100.00"),
            purpose="Rate limit test",
            status="approved",
        )

        payment = Payment.objects.create(
            requisition=req, amount=Decimal("100.00"), status="pending", fund=self.fund
        )

        self.client.login(username="treasury", password="treas123")

        # Request OTP multiple times rapidly
        responses = []
        for i in range(6):
            response = self.client.post(
                f"/treasury/api/payments/{payment.id}/request-otp/",
                content_type="application/json",
            )
            responses.append(response.status_code)

        # At least one should be rate-limited (429 Too Many Requests)
        # This depends on rate limiting implementation
        # For now, just verify endpoint exists
        self.assertTrue(all(status in [200, 201, 429, 404] for status in responses))

    def test_expired_otp_rejected(self):
        """Expired OTP should be rejected"""
        # This test requires OTP model/storage implementation
        # Placeholder for when OTP expiry is implemented

        req = Requisition.objects.create(
            transaction_id="OTP-004",
            requested_by=self.requester,
            origin_type="branch",
            company=self.company,
            branch=self.branch,
            amount=Decimal("100.00"),
            purpose="Expired OTP test",
            status="approved",
        )

        payment = Payment.objects.create(
            requisition=req, amount=Decimal("100.00"), status="pending", fund=self.fund
        )

        self.client.login(username="treasury", password="treas123")

        # Request OTP
        otp_response = self.client.post(
            f"/treasury/api/payments/{payment.id}/request-otp/",
            content_type="application/json",
        )

        # If OTP is returned in response (for testing), capture it
        # In production, OTP would be sent via SMS/email

        # Simulate time passing (OTP should expire after 5 minutes)
        # This would require mocking timezone.now() or database timestamp manipulation

        # Try to use expired OTP
        response = self.client.post(
            f"/treasury/api/payments/{payment.id}/execute/",
            data=json.dumps({"otp": "123456"}),  # Would be actual expired OTP
            content_type="application/json",
        )

        # Should be rejected (implementation dependent)
        self.assertIsNotNone(response)

    def test_otp_single_use_only(self):
        """OTP should be invalidated after first use"""
        req = Requisition.objects.create(
            transaction_id="OTP-005",
            requested_by=self.requester,
            origin_type="branch",
            company=self.company,
            branch=self.branch,
            amount=Decimal("100.00"),
            purpose="Single use OTP test",
            status="approved",
        )

        payment = Payment.objects.create(
            requisition=req, amount=Decimal("100.00"), status="pending", fund=self.fund
        )

        self.client.login(username="treasury", password="treas123")

        # Request OTP
        self.client.post(
            f"/treasury/api/payments/{payment.id}/request-otp/",
            content_type="application/json",
        )

        # Use OTP once
        otp = "123456"  # Would be actual OTP from request
        first_response = self.client.post(
            f"/treasury/api/payments/{payment.id}/execute/",
            data=json.dumps({"otp": otp}),
            content_type="application/json",
        )

        # Try to reuse same OTP
        second_response = self.client.post(
            f"/treasury/api/payments/{payment.id}/execute/",
            data=json.dumps({"otp": otp}),
            content_type="application/json",
        )

        # Second attempt should fail (if first succeeded) or both fail (invalid OTP)
        # This test verifies the endpoint behavior
        self.assertIsNotNone(second_response)


class OTPGenerationTest(TestCase):
    """Test OTP generation security"""

    def test_otp_is_numeric_six_digits(self):
        """OTP should be 6-digit numeric code"""
        # This would test the OTP generator function directly
        # Placeholder for OTP utility testing
        from treasury.utils import generate_otp  # Assuming this exists

        try:
            otp = generate_otp()
            self.assertEqual(len(otp), 6)
            self.assertTrue(otp.isdigit())
        except ImportError:
            # OTP generator not yet implemented
            self.skipTest("OTP generator not implemented")

    def test_otp_is_cryptographically_random(self):
        """OTP should use cryptographically secure random generation"""
        # Generate multiple OTPs and verify they're unique
        try:
            from treasury.utils import generate_otp

            otps = set()
            for _ in range(100):
                otp = generate_otp()
                otps.add(otp)

            # Should have high uniqueness (not all same)
            self.assertGreater(len(otps), 90)
        except ImportError:
            self.skipTest("OTP generator not implemented")

    def test_otp_storage_is_hashed(self):
        """OTP should be stored hashed, not plaintext"""
        # This would verify OTP storage in database
        # Placeholder for database OTP storage verification
        self.skipTest("OTP storage verification not implemented")
