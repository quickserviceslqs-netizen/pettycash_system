from datetime import timedelta
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


LOCKOUT_THRESHOLD = 5  # attempts
LOCKOUT_WINDOW_MINUTES = 15


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    # Reset counters on successful login
    user.failed_login_attempts = 0
    user.lockout_until = None
    user.last_login_ip = request.META.get('REMOTE_ADDR')
    user.last_login_user_agent = request.META.get('HTTP_USER_AGENT', '')[:1024]
    user.save(update_fields=['failed_login_attempts', 'lockout_until', 'last_login_ip', 'last_login_user_agent'])

    # Store basic session context for session management
    try:
        request.session['login_time'] = timezone.now().isoformat()
        request.session['ip'] = user.last_login_ip
        request.session['ua'] = user.last_login_user_agent
    except Exception:
        pass


@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request, **kwargs):
    username = (credentials or {}).get('username') or (credentials or {}).get('email')
    if not username:
        return
    try:
        user = User.objects.get(username__iexact=username)
    except User.DoesNotExist:
        return

    now = timezone.now()
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    user.last_failed_login = now

    if user.failed_login_attempts >= LOCKOUT_THRESHOLD:
        user.lockout_until = now + timedelta(minutes=LOCKOUT_WINDOW_MINUTES)

    user.save(update_fields=['failed_login_attempts', 'last_failed_login', 'lockout_until'])


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    # Nothing heavy for now; placeholder if we want to track
    return
