"""
Multi-Tenancy Middleware
Sets company context for each request based on authenticated user.
"""

from threading import local

from django.utils.deprecation import MiddlewareMixin

# Thread-local storage for current company context
_thread_locals = local()


def get_current_company():
    """Get the current company from thread-local storage."""
    return getattr(_thread_locals, "company", None)


def get_current_user():
    """Get the current user from thread-local storage."""
    return getattr(_thread_locals, "user", None)


def set_current_company(company):
    """Set the current company in thread-local storage (for testing)."""
    _thread_locals.company = company


def set_current_user(user):
    """Set the current user in thread-local storage (for testing)."""
    _thread_locals.user = user


class CompanyMiddleware(MiddlewareMixin):
    """
    Middleware to set the current company context for each request.

    This enables automatic filtering of querysets by company without
    needing to explicitly filter in every view.
    """

    def process_request(self, request):
        """Store user and their company in thread-local storage."""
        user = getattr(request, "user", None)

        if user and user.is_authenticated:
            _thread_locals.user = user
            _thread_locals.company = user.company
        else:
            _thread_locals.user = None
            _thread_locals.company = None

    def process_response(self, request, response):
        """Clean up thread-local storage after request."""
        if hasattr(_thread_locals, "user"):
            del _thread_locals.user
        if hasattr(_thread_locals, "company"):
            del _thread_locals.company

        return response
