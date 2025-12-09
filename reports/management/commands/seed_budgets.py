from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from decimal import Decimal, InvalidOperation
import csv
from typing import Optional

from reports.models import BudgetAllocation
from organization.models import Company, Branch, Department, CostCenter


class Command(BaseCommand):
    help = (
        "Seed BudgetAllocation records either from a CSV file or by generating\n"
        "defaults for all branches/departments/cost centers in a company.\n\n"
        "CSV columns: company_id,branch_id,department_id,cost_center_id,year,month,amount\n"
        "- If company_id is omitted per row, --company-id is used.\n"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--company-id",
            type=int,
            help="Company ID (required unless CSV has company_id per row)",
        )
        parser.add_argument(
            "--company-name",
            type=str,
            help="Company name (alternative to --company-id)",
        )
        parser.add_argument(
            "--year", type=int, required=True, help="Target year for allocations"
        )
        parser.add_argument(
            "--csv", type=str, help="Path to CSV file with budget allocations"
        )
        parser.add_argument(
            "--scope",
            type=str,
            choices=["company", "branch", "department", "cost_center"],
            default="cost_center",
            help="Scope to generate budgets for when not using --csv",
        )
        parser.add_argument(
            "--amount",
            type=str,
            help="Default amount to allocate (required when not using --csv)",
        )
        parser.add_argument(
            "--monthly",
            action="store_true",
            help="Generate monthly allocations (12 records) instead of annual",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite amount if allocation already exists",
        )

    def handle(self, *args, **options):
        company = self._resolve_company(options)
        year = options["year"]
        csv_path = options.get("csv")

        if csv_path:
            self._seed_from_csv(
                csv_path,
                default_company=company,
                default_year=year,
                overwrite=options["overwrite"],
            )
        else:
            amount = options.get("amount")
            if amount is None:
                raise CommandError("--amount is required when not using --csv")
            try:
                default_amount = Decimal(amount)
            except InvalidOperation:
                raise CommandError("Invalid --amount, must be a decimal number")

            scope = options["scope"]
            monthly = options["monthly"]
            self._generate_defaults(
                company, year, scope, default_amount, monthly, options["overwrite"]
            )

        self.stdout.write(self.style.SUCCESS("Budget seeding completed."))

    def _resolve_company(self, options) -> Optional[Company]:
        company_id = options.get("company_id")
        company_name = options.get("company_name")

        if company_id:
            try:
                return Company.objects.get(id=company_id)
            except Company.DoesNotExist:
                raise CommandError(f"Company with id={company_id} does not exist")
        if company_name:
            try:
                return Company.objects.get(name=company_name)
            except Company.DoesNotExist:
                raise CommandError(f'Company with name="{company_name}" does not exist')
        # If using CSV, allow company to be resolved per row
        if options.get("csv"):
            return None
        raise CommandError("Provide --company-id or --company-name")

    @transaction.atomic
    def _seed_from_csv(
        self,
        csv_path: str,
        default_company: Optional[Company],
        default_year: int,
        overwrite: bool,
    ):
        created, updated = 0, 0
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            required = {"year", "amount"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise CommandError(
                    f'CSV missing required columns: {", ".join(sorted(missing))}'
                )

            for idx, row in enumerate(reader, start=2):  # header at line 1
                try:
                    company = default_company
                    if row.get("company_id"):
                        company = Company.objects.get(id=int(row["company_id"]))
                    if not company:
                        raise CommandError(
                            "company_id missing and no default company provided"
                        )

                    branch = (
                        Branch.objects.get(id=int(row["branch_id"]))
                        if row.get("branch_id")
                        else None
                    )
                    department = (
                        Department.objects.get(id=int(row["department_id"]))
                        if row.get("department_id")
                        else None
                    )
                    cost_center = (
                        CostCenter.objects.get(id=int(row["cost_center_id"]))
                        if row.get("cost_center_id")
                        else None
                    )

                    year = int(row.get("year") or default_year)
                    month = int(row["month"]) if row.get("month") else None
                    amount = Decimal(row["amount"])
                except Exception as e:
                    raise CommandError(f"CSV parse error at line {idx}: {e}")

                obj, was_created = BudgetAllocation.objects.get_or_create(
                    company=company,
                    branch=branch,
                    department=department,
                    cost_center=cost_center,
                    year=year,
                    month=month,
                    defaults={"amount": amount},
                )
                if was_created:
                    created += 1
                else:
                    if overwrite:
                        obj.amount = amount
                        obj.save(update_fields=["amount"])
                        updated += 1
        self.stdout.write(f"Created: {created}, Updated: {updated}")

    @transaction.atomic
    def _generate_defaults(
        self,
        company: Company,
        year: int,
        scope: str,
        amount: Decimal,
        monthly: bool,
        overwrite: bool,
    ):
        created, updated = 0, 0
        if scope == "company":
            targets = [(None, None, None)]  # branch, department, cost_center
        elif scope == "branch":
            targets = [
                (b, None, None) for b in Branch.objects.filter(region__company=company)
            ]
        elif scope == "department":
            targets = [
                (None, d, None)
                for d in Department.objects.filter(branch__region__company=company)
            ]
        else:  # cost_center
            targets = [
                (None, None, c)
                for c in CostCenter.objects.filter(
                    department__branch__region__company=company
                )
            ]

        months = range(1, 13) if monthly else [None]
        for branch, department, cost_center in targets:
            for m in months:
                obj, was_created = BudgetAllocation.objects.get_or_create(
                    company=company,
                    branch=branch,
                    department=department,
                    cost_center=cost_center,
                    year=year,
                    month=m,
                    defaults={"amount": amount},
                )
                if was_created:
                    created += 1
                else:
                    if overwrite:
                        obj.amount = amount
                        obj.save(update_fields=["amount"])
                        updated += 1
        self.stdout.write(f"Created: {created}, Updated: {updated}")
