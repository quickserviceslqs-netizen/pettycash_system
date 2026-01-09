from django.core import mail
from django.test import TestCase
from django.core.management import call_command
from django.conf import settings

from .services import send_email
from .models import Notification


class EmailTests(TestCase):
    def test_send_email_service(self):
        """send_email should send and return True and be captured by locmem backend"""
        # Ensure test settings use locmem backend
        self.assertEqual(settings.EMAIL_BACKEND, "django.core.mail.backends.locmem.EmailBackend")

        ok = send_email(to_email="user@example.com", subject="Hello", body="Test body")
        self.assertTrue(ok)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, "Hello")
        self.assertIn("Test body", message.body)

    def test_send_test_email_command(self):
        call_command("send_test_email", "--to=user2@example.com")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["user2@example.com"]) 
