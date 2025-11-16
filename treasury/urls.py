from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from treasury.views import (
    TreasuryFundViewSet, PaymentViewSet, 
    VarianceAdjustmentViewSet, ReplenishmentRequestViewSet,
    LedgerEntryViewSet, DashboardViewSet, AlertsViewSet,
    PaymentTrackingViewSet, ReportingViewSet
)

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

# HTML Views for Phase 6
html_patterns = [
    path('dashboard/', TemplateView.as_view(template_name='treasury/dashboard.html'), name='dashboard_view'),
    path('payment-execute/', TemplateView.as_view(template_name='treasury/payment_execute.html'), name='payment_execute'),
    path('funds/', TemplateView.as_view(template_name='treasury/funds.html'), name='funds_view'),
    path('alerts/', TemplateView.as_view(template_name='treasury/alerts.html'), name='alerts_view'),
    path('variances/', TemplateView.as_view(template_name='treasury/variances.html'), name='variances_view'),
]

# URL patterns
urlpatterns = [
    path('', include(html_patterns)),
    path('api/', include(router.urls)),
]

