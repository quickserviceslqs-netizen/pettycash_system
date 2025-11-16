from django.urls import path, include
from rest_framework.routers import DefaultRouter
from treasury.views import (
    TreasuryFundViewSet, PaymentViewSet, 
    VarianceAdjustmentViewSet, ReplenishmentRequestViewSet,
    LedgerEntryViewSet
)

# Setup DRF router for API endpoints
router = DefaultRouter()
router.register(r'funds', TreasuryFundViewSet, basename='fund')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'variances', VarianceAdjustmentViewSet, basename='variance')
router.register(r'replenishments', ReplenishmentRequestViewSet, basename='replenishment')
router.register(r'ledger', LedgerEntryViewSet, basename='ledger')

# URL patterns
urlpatterns = [
    path('api/', include(router.urls)),
]
