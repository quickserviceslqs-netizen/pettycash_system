"""
Custom permission classes for granular access control.
Extends DjangoModelPermissions to check permissions on all HTTP methods including GET.
"""

from rest_framework import permissions


class DjangoModelPermissionsWithView(permissions.DjangoModelPermissions):
    """
    Extended DjangoModelPermissions that also checks view permission for GET requests.

    Default DjangoModelPermissions only checks permissions on write operations.
    This class enforces view permission on read operations too.

    Permissions required:
    - GET (list/retrieve): view permission
    - POST (create): add permission
    - PUT/PATCH (update): change permission
    - DELETE (destroy): delete permission
    """

    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }


class RequireAppAccess(permissions.BasePermission):
    """
    Check if user has access to a specific app before allowing any action.

    Usage in viewset:
        class MyViewSet(viewsets.ModelViewSet):
            permission_classes = [RequireAppAccess]
            required_app = 'treasury'  # Set this attribute
    """

    def has_permission(self, request, view):
        # Check if viewset specifies required_app
        if not hasattr(view, "required_app"):
            return True  # No app requirement specified

        required_app = view.required_app

        # Get user's assigned apps
        user = request.user
        if not user.is_authenticated:
            return False

        # Superusers bypass all app access checks
        if user.is_superuser:
            return True

        # Check if user has this app assigned
        has_app = user.assigned_apps.filter(name=required_app, is_active=True).exists()

        return has_app
