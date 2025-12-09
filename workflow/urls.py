from django.urls import path

from workflow.views import threshold_edit, workflow_dashboard
from workflow.views_admin import (
    create_threshold,
    delete_threshold,
    edit_threshold,
    manage_thresholds,
    toggle_threshold_status,
)

app_name = "workflow"

urlpatterns = [
    path("", workflow_dashboard, name="dashboard"),
    path("threshold/<int:threshold_id>/edit/", threshold_edit, name="threshold_edit"),
    # Admin threshold management
    path("admin/thresholds/", manage_thresholds, name="manage_thresholds"),
    path("admin/thresholds/create/", create_threshold, name="create_threshold"),
    path(
        "admin/thresholds/<int:threshold_id>/edit/",
        edit_threshold,
        name="edit_threshold",
    ),
    path(
        "admin/thresholds/<int:threshold_id>/delete/",
        delete_threshold,
        name="delete_threshold",
    ),
    path(
        "admin/thresholds/<int:threshold_id>/toggle/",
        toggle_threshold_status,
        name="toggle_threshold_status",
    ),
]
