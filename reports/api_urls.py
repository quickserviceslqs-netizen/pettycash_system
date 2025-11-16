from rest_framework.routers import DefaultRouter
from django.urls import path, include
from django.http import QueryDict

from treasury.views import ReportingViewSet

router = DefaultRouter()
# Register at root so actions like /payment_summary/ and /fund_health/ are available
router.register(r'', ReportingViewSet, basename='reporting')

# Direct DRF view for the export action
export_view = ReportingViewSet.as_view({'get': 'export'})

def export_by_type(request, report_type):
    """Wrapper to support /api/reporting/<report_type>/export/ by injecting type into query params."""
    # Make a mutable copy of GET params and inject report type
    q = request.GET.copy()
    q['type'] = report_type
    request.GET = q
    return export_view(request)

urlpatterns = [
    path('', include(router.urls)),
    path('<str:report_type>/export/', export_by_type, name='reporting-export-by-type'),
]
