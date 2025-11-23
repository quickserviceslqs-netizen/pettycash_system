from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter
from treasury.views import (
    TreasuryFundViewSet, PaymentViewSet, 
    VarianceAdjustmentViewSet, ReplenishmentRequestViewSet,
    LedgerEntryViewSet, DashboardViewSet, AlertsViewSet,
    PaymentTrackingViewSet, ReportingViewSet, mpesa_callback,
    treasury_home, treasury_dashboard, payment_execute, 
    funds_view, alerts_view, variances_view
)

app_name = 'treasury'

# Setup DRF router for API endpoints
router = DefaultRouter()
router.register(r'funds', TreasuryFundViewSet, basename='fund')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'variances', VarianceAdjustmentViewSet, basename='variance')
router.register(r'replenishments', ReplenishmentRequestViewSet, basename='replenishment')
router.register(r'ledger', LedgerEntryViewSet, basename='ledger')

# Phase 6: Dashboard & Reporting
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'alerts', AlertsViewSet, basename='alert')
router.register(r'tracking', PaymentTrackingViewSet, basename='tracking')
router.register(r'reports', ReportingViewSet, basename='report')

# HTML Views for Phase 6 - with permission checks
html_patterns = [
    # Default index for /treasury/ -> check access and redirect
    path('', treasury_home, name='index'),
    path('dashboard/', treasury_dashboard, name='dashboard_view'),
    path('payment-execute/', payment_execute, name='payment_execute'),
    path('funds/', funds_view, name='funds_view'),
    path('alerts/', alerts_view, name='alerts_view'),
    path('variances/', variances_view, name='variances_view'),
]

# URL patterns
urlpatterns = [
    path('', include(html_patterns)),
    path('api/', include(router.urls)),
    path('api/mpesa/callback/', mpesa_callback, name='mpesa-callback'),  # M-Pesa callback endpoint
]

