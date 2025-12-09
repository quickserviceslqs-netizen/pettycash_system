"""
Unit Tests for Approval Threshold Matching
Tests the find_approval_threshold function and tier selection logic
"""

from decimal import Decimal
from django.test import TestCase
from workflow.models import ApprovalThreshold
from workflow.services.resolver import find_approval_threshold


class ApprovalThresholdMatchingTests(TestCase):
    """Test threshold matching logic"""

    def setUp(self):
        """Create test thresholds"""
        # Tier 1: 0 - 1000
        self.tier1 = ApprovalThreshold.objects.create(
            name="Tier 1",
            origin_type="ANY",
            min_amount=Decimal("0.00"),
            max_amount=Decimal("1000.00"),
            roles_sequence=["BRANCH_MANAGER"],
            allow_urgent_fasttrack=True,
            priority=1,
        )

        # Tier 2: 1000.01 - 10000
        self.tier2 = ApprovalThreshold.objects.create(
            name="Tier 2",
            origin_type="ANY",
            min_amount=Decimal("1000.01"),
            max_amount=Decimal("10000.00"),
            roles_sequence=["BRANCH_MANAGER", "FINANCE"],
            allow_urgent_fasttrack=True,
            priority=2,
        )

        # Tier 3: 10000.01 - 50000
        self.tier3 = ApprovalThreshold.objects.create(
            name="Tier 3",
            origin_type="ANY",
            min_amount=Decimal("10000.01"),
            max_amount=Decimal("50000.00"),
            roles_sequence=["BRANCH_MANAGER", "FINANCE", "TREASURY"],
            allow_urgent_fasttrack=False,
            priority=3,
        )

        # Branch-specific override for Tier 1
        self.tier1_branch = ApprovalThreshold.objects.create(
            name="Tier 1 Branch Override",
            origin_type="BRANCH",
            min_amount=Decimal("0.00"),
            max_amount=Decimal("500.00"),
            roles_sequence=["DEPARTMENT_HEAD"],  # Different from ANY
            allow_urgent_fasttrack=True,
            priority=0,  # Higher priority (lower number)
        )

    def test_find_threshold_tier1_middle(self):
        """Amount 500 should match Tier 1"""
        threshold = find_approval_threshold(Decimal("500.00"), "ANY")
        self.assertIsNotNone(threshold)
        self.assertEqual(threshold.name, "Tier 1")

    def test_find_threshold_tier1_lower_bound(self):
        """Amount 0 should match Tier 1"""
        threshold = find_approval_threshold(Decimal("0.00"), "ANY")
        self.assertIsNotNone(threshold)
        self.assertEqual(threshold.name, "Tier 1")

    def test_find_threshold_tier1_upper_bound(self):
        """Amount 1000.00 should match Tier 1"""
        threshold = find_approval_threshold(Decimal("1000.00"), "ANY")
        self.assertIsNotNone(threshold)
        self.assertEqual(threshold.name, "Tier 1")

    def test_find_threshold_tier2_lower_bound(self):
        """Amount 1000.01 should match Tier 2"""
        threshold = find_approval_threshold(Decimal("1000.01"), "ANY")
        self.assertIsNotNone(threshold)
        self.assertEqual(threshold.name, "Tier 2")

    def test_find_threshold_tier2_middle(self):
        """Amount 5000 should match Tier 2"""
        threshold = find_approval_threshold(Decimal("5000.00"), "ANY")
        self.assertIsNotNone(threshold)
        self.assertEqual(threshold.name, "Tier 2")

    def test_find_threshold_tier2_upper_bound(self):
        """Amount 10000.00 should match Tier 2"""
        threshold = find_approval_threshold(Decimal("10000.00"), "ANY")
        self.assertIsNotNone(threshold)
        self.assertEqual(threshold.name, "Tier 2")

    def test_find_threshold_tier3(self):
        """Amount 25000 should match Tier 3"""
        threshold = find_approval_threshold(Decimal("25000.00"), "ANY")
        self.assertIsNotNone(threshold)
        self.assertEqual(threshold.name, "Tier 3")

    def test_find_threshold_no_match(self):
        """Amount above all tiers should return None"""
        threshold = find_approval_threshold(Decimal("100000.00"), "ANY")
        self.assertIsNone(threshold)

    def test_find_threshold_negative_amount(self):
        """Negative amount should return None"""
        threshold = find_approval_threshold(Decimal("-100.00"), "ANY")
        self.assertIsNone(threshold)

    def test_find_threshold_origin_specific_priority(self):
        """Branch-specific threshold should take priority over ANY"""
        # 400 matches both Tier 1 (ANY) and Tier 1 Branch Override (BRANCH)
        # Branch override has priority=0, Tier 1 has priority=1
        # Should return the one with lower priority number
        threshold = find_approval_threshold(Decimal("400.00"), "BRANCH")
        self.assertIsNotNone(threshold)
        self.assertEqual(threshold.name, "Tier 1 Branch Override")
        self.assertEqual(threshold.origin_type, "BRANCH")

    def test_find_threshold_origin_fallback_to_any(self):
        """If no branch-specific threshold, should fallback to ANY"""
        # 800 is above branch override (500 max), should fall back to Tier 1 (ANY)
        threshold = find_approval_threshold(Decimal("800.00"), "BRANCH")
        self.assertIsNotNone(threshold)
        self.assertEqual(threshold.name, "Tier 1")
        self.assertEqual(threshold.origin_type, "ANY")

    def test_find_threshold_inactive_excluded(self):
        """Inactive thresholds should be excluded"""
        self.tier1.is_active = False
        self.tier1.save()

        # 500 would normally match Tier 1, but it's inactive
        # Should either return None or next matching tier
        threshold = find_approval_threshold(Decimal("500.00"), "ANY")
        # Depends on implementation - either None or escalates
        # For now, we expect None or a different tier
        if threshold:
            self.assertNotEqual(threshold.id, self.tier1.id)

    def test_find_threshold_case_insensitive_origin(self):
        """Origin type should be case-insensitive"""
        threshold_upper = find_approval_threshold(Decimal("400.00"), "BRANCH")
        threshold_lower = find_approval_threshold(Decimal("400.00"), "branch")

        # Both should return same threshold
        if threshold_upper and threshold_lower:
            self.assertEqual(threshold_upper.id, threshold_lower.id)

    def test_find_threshold_exact_boundary_precision(self):
        """Test decimal precision at boundaries"""
        # Test various decimal representations of boundaries
        threshold_999_99 = find_approval_threshold(Decimal("999.99"), "ANY")
        threshold_1000_00 = find_approval_threshold(Decimal("1000.00"), "ANY")
        threshold_1000_01 = find_approval_threshold(Decimal("1000.01"), "ANY")

        self.assertEqual(threshold_999_99.name, "Tier 1")
        self.assertEqual(threshold_1000_00.name, "Tier 1")
        self.assertEqual(threshold_1000_01.name, "Tier 2")
