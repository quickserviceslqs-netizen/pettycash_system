from django.core.management.base import BaseCommand

from notifications.services import send_email


class Command(BaseCommand):
    help = "Send a test email to the supplied address."

    def add_arguments(self, parser):
        parser.add_argument("--to", dest="to", required=True, help="Recipient email address")
        parser.add_argument("--subject", dest="subject", default="Test Email from Petty Cash System")
        parser.add_argument("--body", dest="body", default="This is a test email sent by management command.")

    def handle(self, *args, **options):
        to = options["to"]
        subject = options["subject"]
        body = options["body"]

        ok = send_email(to_email=to, subject=subject, body=body)
        if ok:
            self.stdout.write(self.style.SUCCESS(f"Email sent to {to}"))
        else:
            self.stderr.write(self.style.ERROR(f"Failed to send email to {to}"))
