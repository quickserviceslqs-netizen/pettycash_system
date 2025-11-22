"""
Permission decorators for granular access control.
Use these to check Django permissions for add/view/change/delete actions.
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied


def require_app_access(app_name):
    """
    Decorator to check if user has access to an app.
    
    Usage:
        @require_app_access('treasury')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped_view(request, *args, **kwargs):
            user = request.user
            
            # Check if user has this app assigned (NO fallback to roles)
            has_app = user.assigned_apps.filter(name=app_name, is_active=True).exists()
            
            if not has_app:
                messages.error(request, f"You don't have access to {app_name.capitalize()} app.")
                return redirect('dashboard')
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


def require_permission(permission_codename, app_label=None, redirect_to='dashboard'):
    """
    Decorator to check if user has a specific Django permission.
    
    Usage:
        @require_permission('treasury.change_payment')
        def edit_payment(request, payment_id):
            ...
        
        Or with separate parameters:
        @require_permission('change_payment', app_label='treasury')
        def edit_payment(request, payment_id):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped_view(request, *args, **kwargs):
            # Build permission string
            if app_label:
                perm = f"{app_label}.{permission_codename}"
            else:
                perm = permission_codename
            
            # Check permission
            if not request.user.has_perm(perm):
                messages.error(
                    request, 
                    f"You don't have permission to perform this action. Required: {perm}"
                )
                return redirect(redirect_to)
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


def check_permission(user, permission_codename, app_label=None):
    """
    Helper function to check permission programmatically.
    
    Usage:
        if check_permission(request.user, 'change_payment', 'treasury'):
            # User can edit payments
    """
    if app_label:
        perm = f"{app_label}.{permission_codename}"
    else:
        perm = permission_codename
    
    return user.has_perm(perm)


def get_user_apps(user):
    """
    Get list of apps a user has access to.
    Returns app names as list of strings (NO role fallback).
    
    Usage:
        apps = get_user_apps(request.user)
        if 'treasury' in apps:
            # Show treasury features
    """
    # Get assigned apps only
    assigned = list(user.assigned_apps.filter(is_active=True).values_list('name', flat=True))
    return assigned
