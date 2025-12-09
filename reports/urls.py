from django.urls import path
from . import views

app_name = "reports"

# ---------------------------------------------------------------------
# URL patterns
# ---------------------------------------------------------------------
urlpatterns = [
    # Main dashboard
    path("", views.reports_dashboard, name="dashboard"),
    path("dashboard/", views.reports_dashboard, name="reports-dashboard"),
    # Detailed reports
    path("transactions/", views.transaction_report, name="transaction-report"),
    path(
        "transactions/export/csv",
        views.transaction_report_export_csv,
        name="transaction-report-export-csv",
    ),
    path(
        "transactions/export/xlsx",
        views.transaction_report_export_xlsx,
        name="transaction-report-export-xlsx",
    ),
    path("treasury/", views.treasury_report, name="treasury-report"),
    path(
        "treasury/fund/<uuid:fund_id>/",
        views.treasury_fund_detail,
        name="treasury-fund-detail",
    ),
    path(
        "treasury/fund/<uuid:fund_id>/export/ledger.csv",
        views.treasury_fund_ledger_export_csv,
        name="treasury-fund-ledger-export-csv",
    ),
    path(
        "treasury/fund/<uuid:fund_id>/export/ledger.xlsx",
        views.treasury_fund_ledger_export_xlsx,
        name="treasury-fund-ledger-export-xlsx",
    ),
    path(
        "treasury/fund/<uuid:fund_id>/export/payments.csv",
        views.treasury_fund_payments_export_csv,
        name="treasury-fund-payments-export-csv",
    ),
    path(
        "treasury/fund/<uuid:fund_id>/export/payments.xlsx",
        views.treasury_fund_payments_export_xlsx,
        name="treasury-fund-payments-export-xlsx",
    ),
    path("approvals/", views.approval_report, name="approval-report"),
    path(
        "approvals/export/logs.csv",
        views.approval_logs_export_csv,
        name="approval-logs-export-csv",
    ),
    path(
        "approvals/export/logs.xlsx",
        views.approval_logs_export_xlsx,
        name="approval-logs-export-xlsx",
    ),
    path(
        "approvals/export/approvers.csv",
        views.approver_perf_export_csv,
        name="approver-perf-export-csv",
    ),
    path(
        "approvals/export/approvers.xlsx",
        views.approver_perf_export_xlsx,
        name="approver-perf-export-xlsx",
    ),
    path("user-activity/", views.user_activity_report, name="user-activity-report"),
    # Budget vs Actuals
    path(
        "budget-vs-actuals/", views.budget_vs_actuals_report, name="budget-vs-actuals"
    ),
    path(
        "budget-vs-actuals/export.csv",
        views.budget_vs_actuals_export_csv,
        name="budget-vs-actuals-export-csv",
    ),
    path(
        "budget-vs-actuals/export.xlsx",
        views.budget_vs_actuals_export_xlsx,
        name="budget-vs-actuals-export-xlsx",
    ),
    # Exceptions
    path(
        "exceptions/stuck-approvals/",
        views.stuck_approvals_report,
        name="stuck-approvals-report",
    ),
    path(
        "exceptions/threshold-overrides/",
        views.threshold_overrides_report,
        name="threshold-overrides-report",
    ),
    path(
        "exceptions/threshold-overrides/export.csv",
        views.threshold_overrides_export_csv,
        name="threshold-overrides-export-csv",
    ),
    # Phase 1: Quick Win Reports
    path(
        "category-spending/",
        views.category_spending_report,
        name="category-spending-report",
    ),
    path(
        "category-spending/export/csv/",
        views.category_spending_export_csv,
        name="category-spending-export-csv",
    ),
    path(
        "category-spending/export/xlsx/",
        views.category_spending_export_xlsx,
        name="category-spending-export-xlsx",
    ),
    path(
        "payment-methods/",
        views.payment_method_analysis,
        name="payment-method-analysis",
    ),
    path(
        "regional-comparison/",
        views.regional_comparison_report,
        name="regional-comparison",
    ),
    path(
        "rejection-analysis/",
        views.rejection_analysis_report,
        name="rejection-analysis",
    ),
    path("average-metrics/", views.average_metrics_report, name="average-metrics"),
]
