from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone


class LockoutAuthenticationForm(AuthenticationForm):
    """Authentication form that blocks login if user is locked out and shows a clear message."""

    def confirm_login_allowed(self, user):
        # Call parent to honor is_active, etc., after our checks
        lockout_until = getattr(user, "lockout_until", None)
        if lockout_until and lockout_until > timezone.now():
            remaining = int((lockout_until - timezone.now()).total_seconds() // 60) + 1
            raise forms.ValidationError(
                f"Account locked due to too many failed attempts. Try again in about {remaining} minute(s).",
                code="locked",
            )
        return super().confirm_login_allowed(user)
