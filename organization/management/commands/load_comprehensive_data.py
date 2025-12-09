"""
Comprehensive test data loader with all roles for UAT/Production testing.
Creates realistic organizational structure with all approval roles.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import User
from organization.models import Company, Region, Branch, Department
from workflow.models import ApprovalThreshold
from decimal import Decimal


class Command(BaseCommand):
    help = "Load comprehensive test data with all roles"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing test data before loading",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing test data..."))
            # Don't delete admin users
            User.objects.exclude(is_superuser=True).delete()
            Department.objects.all().delete()
            Branch.objects.all().delete()
            Region.objects.all().delete()
            Company.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("✓ Cleared existing data"))

        self.stdout.write("Loading comprehensive test data...")

        # ============= ORGANIZATION STRUCTURE =============
        # Create company
        company, _ = Company.objects.get_or_create(
            name="QuickServices LQS", defaults={"code": "QS001"}
        )
        self.stdout.write(f"✓ Company: {company.name}")

        # Create regions
        nairobi_region, _ = Region.objects.get_or_create(
            name="Nairobi Region", company=company, defaults={"code": "NRB"}
        )

        eldoret_region, _ = Region.objects.get_or_create(
            name="Eldoret Region", company=company, defaults={"code": "ELD"}
        )
        self.stdout.write(f"✓ Regions: {nairobi_region.name}, {eldoret_region.name}")

        # Create branches
        nairobi_branch, _ = Branch.objects.get_or_create(
            name="Nairobi", region=nairobi_region, defaults={"code": "NRB001"}
        )

        eldoret_branch, _ = Branch.objects.get_or_create(
            name="ELDORET", region=eldoret_region, defaults={"code": "ELD001"}
        )
        self.stdout.write(f"✓ Branches: {nairobi_branch.name}, {eldoret_branch.name}")

        # Create departments
        finance_dept, _ = Department.objects.get_or_create(
            name="Finance", branch=nairobi_branch
        )

        operations_dept, _ = Department.objects.get_or_create(
            name="Operations", branch=nairobi_branch
        )
        self.stdout.write(f"✓ Departments: {finance_dept.name}, {operations_dept.name}")

        # ============= USERS WITH ALL ROLES =============
        users_data = [
            # Staff users (Nairobi)
            {
                "username": "N.Nyaga",
                "email": "n.nyaga@quickservices.com",
                "first_name": "Nancy",
                "last_name": "Nyaga",
                "role": "staff",
                "branch": nairobi_branch,
                "department": operations_dept,
            },
            {
                "username": "P.Wafula",
                "email": "p.wafula@quickservices.com",
                "first_name": "Peter",
                "last_name": "Wafula",
                "role": "staff",
                "branch": nairobi_branch,
                "department": operations_dept,
            },
            # Branch Manager (Nairobi)
            {
                "username": "K.Mogare",
                "email": "k.mogare@quickservices.com",
                "first_name": "Kevin",
                "last_name": "Mogare",
                "role": "branch_manager",
                "branch": nairobi_branch,
                "department": operations_dept,
            },
            # Department Head (Nairobi)
            {
                "username": "B.Ghero",
                "email": "b.ghero@quickservices.com",
                "first_name": "Brian",
                "last_name": "Ghero",
                "role": "department_head",
                "branch": nairobi_branch,
                "department": operations_dept,
            },
            # Regional Manager (Nairobi Region)
            {
                "username": "Dwanyiri",
                "email": "d.wanyiri@quickservices.com",
                "first_name": "David",
                "last_name": "Wanyiri",
                "role": "regional_manager",
                "branch": None,
                "department": None,
                "region": nairobi_region,
            },
            # Field Staff (Nairobi Region)
            {
                "username": "J.Kamau",
                "email": "j.kamau@quickservices.com",
                "first_name": "James",
                "last_name": "Kamau",
                "role": "staff",
                "branch": None,  # Field staff not tied to branch
                "department": None,
                "region": nairobi_region,
            },
            {
                "username": "M.Otieno",
                "email": "m.otieno@quickservices.com",
                "first_name": "Mary",
                "last_name": "Otieno",
                "role": "staff",
                "branch": None,  # Field staff not tied to branch
                "department": None,
                "region": nairobi_region,
            },
            # FP&A (Centralized)
            {
                "username": "Vmuindi",
                "email": "v.muindi@quickservices.com",
                "first_name": "Victor",
                "last_name": "Muindi",
                "role": "fp&a",
                "branch": None,
                "department": None,
            },
            # Group Finance Manager (Centralized)
            {
                "username": "Pmaril",
                "email": "p.maril@quickservices.com",
                "first_name": "Paul",
                "last_name": "Maril",
                "role": "group_finance_manager",
                "branch": None,
                "department": None,
            },
            # Treasury (Centralized)
            {
                "username": "Cmartins",
                "email": "c.martins@quickservices.com",
                "first_name": "Carol",
                "last_name": "Martins",
                "role": "treasury",
                "branch": None,
                "department": None,
            },
            # CFO (Centralized)
            {
                "username": "P.musyoki",
                "email": "p.musyoki@quickservices.com",
                "first_name": "Patrick",
                "last_name": "Musyoki",
                "role": "cfo",
                "branch": eldoret_branch,  # CFO can have location but is centralized
                "department": None,
            },
            # CEO (Centralized)
            {
                "username": "S.Bary",
                "email": "s.bary@quickservices.com",
                "first_name": "Samuel",
                "last_name": "Bary",
                "role": "ceo",
                "branch": None,
                "department": None,
            },
        ]

        created_count = 0
        for user_data in users_data:
            region = user_data.pop("region", None)  # Extract region if present
            user, created = User.objects.get_or_create(
                username=user_data["username"],
                defaults={
                    "email": user_data["email"],
                    "first_name": user_data["first_name"],
                    "last_name": user_data["last_name"],
                    "role": user_data["role"],
                    "branch": user_data["branch"],
                    "department": user_data["department"],
                    "company": company,
                    "region": region,  # Set region for field staff
                },
            )
            if created:
                user.set_password("Test@123456")
                user.save()
                created_count += 1
                self.stdout.write(f"  ✓ Created: {user.username} ({user.role})")
            else:
                self.stdout.write(f"  → Exists: {user.username} ({user.role})")

        self.stdout.write(self.style.SUCCESS(f"\n✓ Created {created_count} new users"))
        self.stdout.write(self.style.SUCCESS(f"✓ Total users: {User.objects.count()}"))

        # ============= APPROVAL THRESHOLDS - PHASE 3 RE-ENGINEERED =============
        self.stdout.write("\nSetting up approval thresholds (Phase 3 spec)...")

        thresholds_data = [
            # BRANCH ORIGIN
            # Tier 1: ≤ 10,000 — routine, fast
            # After approval, Treasury validates & executes payment
            {
                "name": "Tier 1 Branch",
                "origin_type": "BRANCH",
                "min_amount": Decimal("0.00"),
                "max_amount": Decimal("10000.00"),
                "roles_sequence": [
                    "branch_manager"
                ],  # Approvals end here, Treasury executes payment
                "priority": 1,
                "allow_urgent_fasttrack": True,
            },
            # Tier 2: 10,001–50,000 — departmental
            # After approvals, Treasury validates & executes payment
            {
                "name": "Tier 2 Branch",
                "origin_type": "BRANCH",
                "min_amount": Decimal("10000.01"),
                "max_amount": Decimal("50000.00"),
                "roles_sequence": [
                    "branch_manager",
                    "department_head",
                ],  # Approvals end here, Treasury executes payment
                "priority": 1,
                "allow_urgent_fasttrack": True,
            },
            # Tier 3: 50,001–250,000 — regional-level
            # After approvals, Treasury validates & executes payment
            {
                "name": "Tier 3 Branch",
                "origin_type": "BRANCH",
                "min_amount": Decimal("50000.01"),
                "max_amount": Decimal("250000.00"),
                "roles_sequence": [
                    "branch_manager",
                    "regional_manager",
                ],  # Approvals end here, Treasury executes payment
                "priority": 1,
                "allow_urgent_fasttrack": True,
            },
            # Tier 4: > 250,000 — HQ-level, CFO required (cannot fast-track)
            # After CFO approval, Treasury validates & executes payment
            {
                "name": "Tier 4 Branch",
                "origin_type": "BRANCH",
                "min_amount": Decimal("250000.01"),
                "max_amount": Decimal("999999999.99"),
                "roles_sequence": [
                    "regional_manager",
                    "cfo",
                ],  # Approvals end here, Treasury executes payment
                "priority": 1,
                "allow_urgent_fasttrack": False,
            },
            # HQ ORIGIN
            # Tier 1: ≤ 10,000 — routine, fast
            # After approval, Treasury validates & executes payment
            {
                "name": "Tier 1 HQ",
                "origin_type": "HQ",
                "min_amount": Decimal("0.00"),
                "max_amount": Decimal("10000.00"),
                "roles_sequence": [
                    "department_head"
                ],  # Approvals end here, Treasury executes payment
                "priority": 1,
                "allow_urgent_fasttrack": True,
            },
            # Tier 2: 10,001–50,000 — departmental
            # After approvals, Treasury validates & executes payment
            {
                "name": "Tier 2 HQ",
                "origin_type": "HQ",
                "min_amount": Decimal("10000.01"),
                "max_amount": Decimal("50000.00"),
                "roles_sequence": [
                    "department_head",
                    "group_finance_manager",
                ],  # Approvals end here, Treasury executes payment
                "priority": 1,
                "allow_urgent_fasttrack": True,
            },
            # Tier 3: 50,001–250,000 — regional-level
            # After approvals, Treasury validates & executes payment
            {
                "name": "Tier 3 HQ",
                "origin_type": "HQ",
                "min_amount": Decimal("50000.01"),
                "max_amount": Decimal("250000.00"),
                "roles_sequence": [
                    "department_head",
                    "group_finance_manager",
                ],  # Approvals end here, Treasury executes payment
                "priority": 1,
                "allow_urgent_fasttrack": True,
            },
            # Tier 4: > 250,000 — HQ-level, CFO required (cannot fast-track)
            # After CFO approval, Treasury validates & executes payment
            {
                "name": "Tier 4 HQ",
                "origin_type": "HQ",
                "min_amount": Decimal("250000.01"),
                "max_amount": Decimal("999999999.99"),
                "roles_sequence": [
                    "group_finance_manager",
                    "cfo",
                ],  # Approvals end here, Treasury executes payment
                "priority": 1,
                "allow_urgent_fasttrack": False,
            },
            # FIELD ORIGIN
            # Tier 1: ≤ 10,000 — routine field expenses
            # Regional Manager approves, then Treasury executes payment
            {
                "name": "Tier 1 Field",
                "origin_type": "FIELD",
                "min_amount": Decimal("0.00"),
                "max_amount": Decimal("10000.00"),
                "roles_sequence": [
                    "regional_manager"
                ],  # Approvals end here, Treasury executes payment
                "priority": 1,
                "allow_urgent_fasttrack": True,
            },
            # Tier 2: 10,001–50,000 — departmental field expenses
            # Regional Manager → Dept Head approve, then Treasury executes payment
            {
                "name": "Tier 2 Field",
                "origin_type": "FIELD",
                "min_amount": Decimal("10000.01"),
                "max_amount": Decimal("50000.00"),
                "roles_sequence": [
                    "regional_manager",
                    "department_head",
                ],  # Approvals end here, Treasury executes payment
                "priority": 1,
                "allow_urgent_fasttrack": True,
            },
            # Tier 3: 50,001–250,000 — regional-level field expenses
            # Regional Manager → CFO approve, then Treasury executes payment
            {
                "name": "Tier 3 Field",
                "origin_type": "FIELD",
                "min_amount": Decimal("50000.01"),
                "max_amount": Decimal("250000.00"),
                "roles_sequence": [
                    "regional_manager",
                    "cfo",
                ],  # Approvals end here, Treasury executes payment
                "priority": 1,
                "allow_urgent_fasttrack": True,
            },
            # Tier 4: > 250,000 — HQ-level field expenses (cannot fast-track)
            # Regional Manager → CFO approve, then Treasury executes payment
            {
                "name": "Tier 4 Field",
                "origin_type": "FIELD",
                "min_amount": Decimal("250000.01"),
                "max_amount": Decimal("999999999.99"),
                "roles_sequence": [
                    "regional_manager",
                    "cfo",
                ],  # Approvals end here, Treasury executes payment
                "priority": 1,
                "allow_urgent_fasttrack": False,
            },
        ]

        threshold_count = 0
        for threshold_data in thresholds_data:
            threshold, created = ApprovalThreshold.objects.get_or_create(
                name=threshold_data["name"], defaults=threshold_data
            )
            if created:
                threshold_count += 1
                self.stdout.write(f"  ✓ Created: {threshold.name}")
            else:
                self.stdout.write(f"  → Exists: {threshold.name}")

        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Created {threshold_count} new thresholds")
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Total thresholds: {ApprovalThreshold.objects.count()}"
            )
        )

        # ============= SUMMARY =============
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 50))
        self.stdout.write(self.style.SUCCESS("TEST DATA LOADED SUCCESSFULLY!"))
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write("\nDefault Password: Test@123456")
        self.stdout.write("\nTest Users by Role:")
        self.stdout.write("  Staff: N.Nyaga, P.Wafula")
        self.stdout.write("  Branch Manager: K.Mogare")
        self.stdout.write("  Department Head: B.Ghero")
        self.stdout.write("  Regional Manager: Dwanyiri")
        self.stdout.write("  FP&A: Vmuindi")
        self.stdout.write("  Group Finance Manager: Pmaril")
        self.stdout.write("  Treasury: Cmartins")
        self.stdout.write("  CFO: P.musyoki")
        self.stdout.write("  CEO: S.Bary")
        self.stdout.write(self.style.SUCCESS("\nReady for testing! 🚀"))
