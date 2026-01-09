# Email Notifications Module 🔔

This document explains the new `notifications` app and how to configure the email settings for different environments.

## Environment variables

- EMAIL_BACKEND (optional) — Default: `django.core.mail.backends.smtp.EmailBackend`.
  - Example for file-based locals: `django.core.mail.backends.console.EmailBackend` (prints to console) or `django.core.mail.backends.locmem.EmailBackend` (captured by tests).
- EMAIL_HOST — SMTP server host (default: `localhost`)
- EMAIL_PORT — SMTP server port (default: `25`)
- EMAIL_HOST_USER — SMTP username
- EMAIL_HOST_PASSWORD — SMTP password
- EMAIL_USE_TLS — `True`/`False`
- EMAIL_USE_SSL — `True`/`False`
- DEFAULT_FROM_EMAIL — Default "from" address for outgoing emails

For most production providers (SendGrid, AWS SES, etc.), set `EMAIL_BACKEND` to the appropriate backend and provide host/credentials via the environment.

## Quick usage

- Send a test email:

```bash
python manage.py send_test_email --to=you@example.com --subject="Hello" --body="Test from Petty Cash System"
```

- Programmatically send an email using the service:

```py
from notifications.services import send_email

send_email('user@example.com', subject='Hello', body='This is a message', save_record=True)
```

- Use templated emails:

```py
from notifications.services import send_templated_email

send_templated_email('user@example.com', 'notifications/email/simple_email.txt', {'body': 'Hi!'}, subject='Templated')
```

## Testing

- `local_test_settings.py` is configured to use `locmem` email backend so tests capture sent messages in `django.core.mail.outbox`.

## Notes

- The `notifications.Notification` model can be used to track delivery status; use `save_record=True` when calling `send_email` to persist.
- For bulk or queued notifications, integrate with Celery or a background task runner and call `send_email` from tasks.
