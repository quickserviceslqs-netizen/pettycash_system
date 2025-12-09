"""
Create sample approval thresholds for production deployment.
Run this script after migrations to seed the workflow app.
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pettycash_system.settings")
django.setup()

from workflow.models import ApprovalThreshold


def create_sample_thresholds():
    """Create default approval thresholds if they don't exist."""

    if ApprovalThreshold.objects.exists():
        print(
            f"✓ {ApprovalThreshold.objects.count()} approval thresholds already exist"
        )
        return

    print("Creating sample approval thresholds...")

    thresholds = [
        {
            "name": "Tier 1 - Small Amounts",
            "origin_type": "ANY",
            "min_amount": 0,
            "max_amount": 10000,
            "roles_sequence": ["branch_manager"],
            "allow_urgent_fasttrack": True,
            "requires_cfo": False,
            "priority": 1,
            "is_active": True,
        },
        {
            "name": "Tier 2 - Medium Amounts",
            "origin_type": "ANY",
            "min_amount": 10001,
            "max_amount": 50000,
            "roles_sequence": ["branch_manager", "department_head"],
            "allow_urgent_fasttrack": True,
            "requires_cfo": False,
            "priority": 2,
            "is_active": True,
        },
        {
            "name": "Tier 3 - Large Amounts",
            "origin_type": "ANY",
            "min_amount": 50001,
            "max_amount": 250000,
            "roles_sequence": ["branch_manager", "regional_manager"],
            "allow_urgent_fasttrack": False,
            "requires_cfo": False,
            "priority": 3,
            "is_active": True,
        },
        {
            "name": "Tier 4 - Very Large Amounts",
            "origin_type": "ANY",
            "min_amount": 250001,
            "max_amount": 999999999,
            "roles_sequence": ["regional_manager", "cfo", "ceo"],
            "allow_urgent_fasttrack": False,
            "requires_cfo": True,
            "requires_ceo": True,
            "priority": 4,
            "is_active": True,
        },
    ]

    for data in thresholds:
        threshold = ApprovalThreshold.objects.create(**data)
        print(f"✓ Created: {threshold.name}")

    print(f"\n✓ Successfully created {len(thresholds)} approval thresholds")


if __name__ == "__main__":
    create_sample_thresholds()
