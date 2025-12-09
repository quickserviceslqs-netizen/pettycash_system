from django.urls import include, path
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter

from treasury.views import (
    AlertsViewSet,
    DashboardViewSet,
    LedgerEntryViewSet,
    PaymentTrackingViewSet,
    PaymentViewSet,
    ReplenishmentRequestViewSet,
    ReportingViewSet,
    TreasuryFundViewSet,
    VarianceAdjustmentViewSet,
    alerts_view,
    funds_view,
    mpesa_callback,
    payment_execute,
    treasury_dashboard,
    treasury_home,
    variances_view,
)
from treasury.views_admin import (
    approve_variance,
    bulk_payment_upload,
    create_fund,
    create_payment,
    create_variance,
    edit_fund,
    execute_payment,
    generate_mpesa_bulk,
    manage_funds,
    manage_payments,
    manage_variances,
    process_bulk_payments,
    select_payments_for_bulk,
    send_to_mpesa_api,
    view_ledger,
)

app_name = "treasury"

# Setup DRF router for API endpoints
router = DefaultRouter()
router.register(r"funds", TreasuryFundViewSet, basename="fund")
router.register(r"payments", PaymentViewSet, basename="payment")
router.register(r"variances", VarianceAdjustmentViewSet, basename="variance")
router.register(
    r"replenishments", ReplenishmentRequestViewSet, basename="replenishment"
)
router.register(r"ledger", LedgerEntryViewSet, basename="ledger")

# Phase 6: Dashboard & Reporting
router.register(r"dashboard", DashboardViewSet, basename="dashboard")
router.register(r"alerts", AlertsViewSet, basename="alert")
router.register(r"tracking", PaymentTrackingViewSet, basename="tracking")
router.register(r"reports", ReportingViewSet, basename="report")

# HTML Views for Phase 6 - with permission checks
html_patterns = [
    # Default index for /treasury/ -> check access and redirect
    path("", treasury_home, name="index"),
    path("dashboard/", treasury_dashboard, name="dashboard_view"),
    path("payment-execute/", payment_execute, name="payment_execute"),
    path("funds/", funds_view, name="funds_view"),
    path("alerts/", alerts_view, name="alerts_view"),
    path("variances/", variances_view, name="variances_view"),
    # Admin treasury management
    path("admin/funds/", manage_funds, name="manage_funds"),
    path("admin/funds/create/", create_fund, name="create_fund"),
    path("admin/funds/<uuid:fund_id>/edit/", edit_fund, name="edit_fund"),
    path("admin/payments/", manage_payments, name="manage_payments"),
    path(
        "admin/payments/create/<uuid:requisition_id>/",
        create_payment,
        name="create_payment",
    ),
    path(
        "admin/payments/<uuid:payment_id>/execute/",
        execute_payment,
        name="execute_payment",
    ),
    # Bulk payment processing (API-based workflow)
    path(
        "admin/bulk-payment/select/",
        select_payments_for_bulk,
        name="select_payments_for_bulk",
    ),
    path(
        "admin/bulk-payment/generate/", generate_mpesa_bulk, name="generate_mpesa_bulk"
    ),
    path("admin/bulk-payment/send-api/", send_to_mpesa_api, name="send_to_mpesa_api"),
    # Alternative: Manual file upload (if needed)
    path("admin/bulk-payment/upload/", bulk_payment_upload, name="bulk_payment_upload"),
    path(
        "admin/bulk-payment/process/",
        process_bulk_payments,
        name="process_bulk_payments",
    ),
    path("admin/ledger/", view_ledger, name="view_ledger"),
    path("admin/variances/", manage_variances, name="manage_variances"),
    path("admin/variances/create/", create_variance, name="create_variance"),
    path(
        "admin/variances/<uuid:variance_id>/approve/",
        approve_variance,
        name="approve_variance",
    ),
]

# URL patterns
urlpatterns = [
    path("", include(html_patterns)),
    path("api/", include(router.urls)),
    path(
        "api/mpesa/callback/", mpesa_callback, name="mpesa-callback"
    ),  # M-Pesa callback endpoint
]
