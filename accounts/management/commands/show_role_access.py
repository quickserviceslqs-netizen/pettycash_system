"""
Display role-based app access matrix.
Usage: python manage.py show_role_access
"""

from django.core.management.base import BaseCommand
from accounts.models import User
from accounts.views import ROLE_ACCESS, APPROVER_ROLES


class Command(BaseCommand):
    help = "Display role-based app access matrix"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 80))
        self.stdout.write(self.style.SUCCESS("ROLE-BASED APP ACCESS MATRIX"))
        self.stdout.write(self.style.SUCCESS("=" * 80 + "\n"))

        # Available apps
        all_apps = set()
        for apps in ROLE_ACCESS.values():
            all_apps.update(apps)
        all_apps = sorted(all_apps)

        # Header
        header = f"{'Role':<25} {'Apps':<40} {'Approver':<10}"
        self.stdout.write(self.style.HTTP_INFO(header))
        self.stdout.write("-" * 80)

        # Role rows
        for role_key, role_display in User.ROLE_CHOICES:
            apps = ROLE_ACCESS.get(role_key, [])
            apps_str = ", ".join(apps) if apps else "None"
            is_approver = "✓" if role_key in APPROVER_ROLES else "-"

            row = f"{role_display:<25} {apps_str:<40} {is_approver:<10}"

            if role_key in ["admin", "ceo", "cfo"]:
                self.stdout.write(self.style.ERROR(row))  # Red for executive
            elif role_key in APPROVER_ROLES:
                self.stdout.write(self.style.WARNING(row))  # Yellow for approvers
            else:
                self.stdout.write(row)

        self.stdout.write("\n" + "=" * 80)

        # Summary
        self.stdout.write(self.style.SUCCESS("\nAPP SUMMARY:"))
        for app in all_apps:
            roles_with_access = [
                dict(User.ROLE_CHOICES)[role]
                for role, apps in ROLE_ACCESS.items()
                if app in apps
            ]
            self.stdout.write(f"  {app:<15} → {', '.join(roles_with_access)}")

        self.stdout.write(self.style.SUCCESS("\nAPPROVER ROLES:"))
        approver_role_names = [
            dict(User.ROLE_CHOICES)[role]
            for role in APPROVER_ROLES
            if role in dict(User.ROLE_CHOICES)
        ]
        self.stdout.write(f"  {', '.join(sorted(approver_role_names))}")

        self.stdout.write("\n" + "=" * 80 + "\n")
