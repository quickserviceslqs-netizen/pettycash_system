"""
URLs for system maintenance module.
"""

from django.urls import path
from . import views

app_name = "system_maintenance"

urlpatterns = [
    # Main dashboard
    path("", views.maintenance_dashboard, name="dashboard"),
    # Backup management
    path("backups/", views.backup_management, name="backup_management"),
    path(
        "backups/<str:backup_id>/download/",
        views.download_backup,
        name="download_backup",
    ),
    # Restore management
    path("restore/", views.restore_management, name="restore_management"),
    # Health checks
    path("health/", views.health_check, name="health_check"),
    path(
        "health/<str:check_id>/", views.health_check_detail, name="health_check_detail"
    ),
    # Maintenance mode
    path("maintenance-mode/", views.maintenance_mode_control, name="maintenance_mode"),
    # Factory reset (superuser only)
    path("factory-reset/", views.factory_reset, name="factory_reset"),
]
