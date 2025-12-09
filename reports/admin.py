import csv
from decimal import Decimal

from django.contrib import admin, messages
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import path, reverse

from organization.models import Branch, Company, CostCenter, Department

from .models import BudgetAllocation, Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "status", "created_by", "created_at")
    list_filter = ("status", "company")
    search_fields = ("title", "description")


@admin.register(BudgetAllocation)
class BudgetAllocationAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "branch",
        "department",
        "cost_center",
        "year",
        "month",
        "amount",
    )
    list_filter = ("company", "year", "month", "branch", "department")
    search_fields = (
        "company__name",
        "branch__name",
        "department__name",
        "cost_center__name",
    )

    actions = ["export_selected_to_csv"]

    def export_selected_to_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=budget_allocations.csv"
        writer = csv.writer(response)
        writer.writerow(
            [
                "company_id",
                "branch_id",
                "department_id",
                "cost_center_id",
                "year",
                "month",
                "amount",
            ]
        )
        for obj in queryset:
            writer.writerow(
                [
                    obj.company_id,
                    obj.branch_id or "",
                    obj.department_id or "",
                    obj.cost_center_id or "",
                    obj.year,
                    obj.month or "",
                    obj.amount,
                ]
            )
        return response

    export_selected_to_csv.short_description = "Export selected to CSV"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name="reports_budgetallocation_import_csv",
            ),
        ]
        return custom + urls

    def import_csv_link(self, request):
        return reverse("admin:reports_budgetallocation_import_csv")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["import_csv_url"] = self.import_csv_link(request)
        return super().changelist_view(request, extra_context=extra_context)

    @transaction.atomic
    def import_csv_view(self, request):
        if request.method == "POST" and request.FILES.get("csv_file"):
            csv_file = request.FILES["csv_file"]
            try:
                decoded = csv_file.read().decode("utf-8").splitlines()
                reader = csv.DictReader(decoded)
                created, updated = 0, 0
                for row in reader:
                    company = (
                        Company.objects.get(id=int(row["company_id"]))
                        if row.get("company_id")
                        else None
                    )
                    if not company:
                        messages.error(request, "company_id is required per row")
                        return HttpResponseRedirect(
                            reverse("admin:reports_budgetallocation_changelist")
                        )
                    branch = (
                        Branch.objects.filter(id=int(row["branch_id"])).first()
                        if row.get("branch_id")
                        else None
                    )
                    department = (
                        Department.objects.filter(id=int(row["department_id"])).first()
                        if row.get("department_id")
                        else None
                    )
                    cost_center = (
                        CostCenter.objects.filter(id=int(row["cost_center_id"])).first()
                        if row.get("cost_center_id")
                        else None
                    )
                    year = int(row["year"])
                    month = int(row["month"]) if row.get("month") else None
                    amount = Decimal(row["amount"])
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
                        obj.amount = amount
                        obj.save(update_fields=["amount"])
                        updated += 1
            except Exception as e:
                messages.error(request, f"Import failed: {e}")
                return HttpResponseRedirect(
                    reverse("admin:reports_budgetallocation_changelist")
                )
            messages.success(
                request, f"Import completed. Created: {created}, Updated: {updated}"
            )
            return HttpResponseRedirect(
                reverse("admin:reports_budgetallocation_changelist")
            )
        # GET renders simple upload form
        return HttpResponse(
            """
			<h2>Import Budget Allocations from CSV</h2>
			<form method="post" enctype="multipart/form-data">
			  <input type="hidden" name="csrfmiddlewaretoken" value="{{ csrf_token }}" />
			  <p>
			    <label>Select CSV file: <input type="file" name="csv_file" accept=".csv" required></label>
			  </p>
			  <p>Required headers: company_id, year, amount. Optional: branch_id, department_id, cost_center_id, month.</p>
			  <button type="submit">Upload & Import</button>
			  <a href="%s" style="margin-left: 1rem;">Back to list</a>
			</form>
			"""
            % reverse("admin:reports_budgetallocation_changelist")
        )
