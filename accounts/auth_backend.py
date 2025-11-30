from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.core.cache import cache
from workflow.services.resolver import (
    get_min_password_length, is_password_complexity_required,
    get_max_login_attempts, get_account_lockout_duration, get_password_change_days,
    get_password_expiry_days, get_rate_limit_login_attempts
)

User = get_user_model()

class SystemSettingAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return None

        # Account lockout logic (pseudo-code, should be implemented with tracking model)
        # if user.is_locked_out():
        #     return None

        # Password validation using security settings
        min_length = get_min_password_length()
        require_complexity = is_password_complexity_required()

        errors = []
        if len(password) < min_length:
            errors.append(f"Password must be at least {min_length} characters.")
        
        if require_complexity:
            if not any(c.isupper() for c in password):
                errors.append("Password must contain an uppercase letter.")
            if not any(c.islower() for c in password):
                errors.append("Password must contain a lowercase letter.")
            if not any(c.isdigit() for c in password):
                errors.append("Password must contain a digit.")
            if not any(not c.isalnum() for c in password):
                errors.append("Password must contain a special character.")

        # Password expiry enforcement (pseudo-code, requires user.last_password_change field)
        if hasattr(user, 'last_password_change'):
            from datetime import datetime, timedelta
            password_expiry_days = get_password_expiry_days()
            if user.last_password_change and (datetime.now() - user.last_password_change).days > password_expiry_days:
                errors.append(f"Password expired. Please change your password.")

        # Rate limiting check
        if request:
            rate_limit_attempts = get_rate_limit_login_attempts()
            if rate_limit_attempts > 0:
                client_ip = self._get_client_ip(request)
                cache_key = f"login_attempts_{client_ip}"
                
                attempts = cache.get(cache_key, 0)
                if attempts >= rate_limit_attempts:
                    errors.append("Too many login attempts. Please try again later.")
                else:
                    # Increment attempts for failed login (will be reset on success)
                    cache.set(cache_key, attempts + 1, 900)  # 15 minutes

        if errors:
            if request:
                for error in errors:
                    from django.contrib import messages
                    messages.error(request, error)
            return None

        if check_password(password, user.password):
            # Reset rate limiting on successful login
            if request:
                client_ip = self._get_client_ip(request)
                cache_key = f"login_attempts_{client_ip}"
                cache.delete(cache_key)
            
            return user if self.user_can_authenticate(user) else None
        else:
            if login_notification_enabled and request:
                # send_login_notification(user, success=False)
                pass
        return None
    
    def _get_client_ip(self, request):
        """Get the client IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip