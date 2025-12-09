from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seeds approval threshold data."

    def handle(self, *args, **options):
        self.stdout.write("Loading approval thresholds fixture...")
        call_command("loaddata", "workflow/fixtures/approval_thresholds.json")
        self.stdout.write(
            self.style.SUCCESS("Approval thresholds seeded successfully.")
        )
