from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from typing import Optional

from .models import Notification


def _get_default_from():
    return getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")


def send_email(
    to_email: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
    from_email: Optional[str] = None,
    save_record: bool = False,
) -> bool:
    """Send an email and optionally persist a Notification record.

    Returns True when send succeeds, False otherwise.
    """
    from_email = from_email or _get_default_from()

    msg = EmailMessage(subject=subject, body=body, from_email=from_email, to=[to_email])
    if html_body:
        msg.content_subtype = "html"
        msg.body = html_body

    if save_record:
        notification = Notification.objects.create(
            to_email=to_email, subject=subject, body=body, html_body=html_body
        )
    else:
        notification = None

    try:
        msg.send(fail_silently=False)
        if notification:
            notification.mark_sent()
        return True
    except Exception as exc:  # pragma: no cover - will be covered implicitly in integration
        if notification:
            notification.mark_failed(str(exc))
        return False


def send_templated_email(
    to_email: str, template_name: str, context: dict, subject: str, save_record: bool = False
) -> bool:
    """Render a text template and send the email."""
    body = render_to_string(template_name, context)
    return send_email(to_email=to_email, subject=subject, body=body, save_record=save_record)
