from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from accounts import views as account_views

# Configure Django Admin
admin.site.site_header = "Petty Cash System Administration"
admin.site.site_title = "Petty Cash Admin"
admin.site.index_title = "Welcome to Petty Cash System Admin"
admin.site.site_url = "/dashboard/"  # "View Site" link goes to user dashboard

urlpatterns = [
    path("admin/", admin.site.urls),
    # Django built-in auth URLs (login/logout/password reset)
    path("accounts/", include("django.contrib.auth.urls")),
    # Your own accounts app URLs
    path("accounts/", include("accounts.urls")),
    # Explicit dashboard route
    path("dashboard/", account_views.dashboard, name="dashboard"),
    # Optional: root redirects to dashboard
    path("", account_views.dashboard, name="home"),
    # Other apps
    path("transactions/", include("transactions.urls")),
    path("treasury/", include("treasury.urls")),
    path("workflow/", include("workflow.urls")),
    path("reports/", include("reports.urls")),
    path("settings/", include("settings_manager.urls")),
    path("organization/", include("organization.urls")),
    path("maintenance/", include("system_maintenance.urls")),
    # API alias for reporting endpoints (keeps legacy JS and templates working)
    path("api/reporting/", include("reports.api_urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
