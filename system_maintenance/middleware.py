"""
Maintenance mode middleware to block access during system maintenance.
"""

from django.conf import settings
from django.shortcuts import render
from django.urls import reverse

from system_maintenance.models import MaintenanceMode


class MaintenanceModeMiddleware:
    """
    Middleware to block non-admin access during maintenance mode.
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # Paths that are always accessible during maintenance
        self.allowed_paths = [
            "/admin/",
            "/static/",
            "/media/",
            "/maintenance/",
        ]

    def __call__(self, request):
        # Check if maintenance mode is active
        if MaintenanceMode.is_maintenance_active():
            # Allow superusers and staff
            if request.user.is_authenticated and (
                request.user.is_superuser or request.user.is_staff
            ):
                response = self.get_response(request)
                return response

            # Check if path is allowed
            path = request.path
            is_allowed = any(path.startswith(allowed) for allowed in self.allowed_paths)

            if not is_allowed:
                # Show maintenance page
                try:
                    maintenance = MaintenanceMode.objects.latest()
                    context = {
                        "maintenance": maintenance,
                        "message": maintenance.custom_message
                        or "System is currently under maintenance",
                        "expected_completion": maintenance.expected_completion,
                    }
                except MaintenanceMode.DoesNotExist:
                    context = {
                        "message": "System is currently under maintenance",
                    }

                return render(
                    request,
                    "system_maintenance/maintenance_mode_page.html",
                    context,
                    status=503,
                )

        response = self.get_response(request)
        return response
