"""
Management command to populate default applications.
Run this after migration to create the 4 core apps.
"""

from django.core.management.base import BaseCommand

from accounts.models import App


class Command(BaseCommand):
    help = "Populate default applications (Transactions, Treasury, Workflow, Reports)"

    def handle(self, *args, **options):
        apps_data = [
            {
                "name": "transactions",
                "display_name": "Transactions",
                "url": "/transactions/",
                "description": "Create and manage requisitions, track transaction status",
                "is_active": True,
            },
            {
                "name": "treasury",
                "display_name": "Treasury",
                "url": "/treasury/",
                "description": "Process payments, manage petty cash funds, reconcile transactions",
                "is_active": True,
            },
            {
                "name": "workflow",
                "display_name": "Workflow",
                "url": "/workflow/",
                "description": "Approve requisitions, manage approval hierarchies",
                "is_active": True,
            },
            {
                "name": "reports",
                "display_name": "Reports",
                "url": "/reports/",
                "description": "View analytics, generate financial reports, track company metrics",
                "is_active": True,
            },
        ]

        created_count = 0
        updated_count = 0

        for app_data in apps_data:
            app, created = App.objects.get_or_create(
                name=app_data["name"], defaults=app_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Created app: {app.display_name}")
                )
                created_count += 1
            else:
                # Update existing app
                for key, value in app_data.items():
                    setattr(app, key, value)
                app.save()
                self.stdout.write(
                    self.style.WARNING(f"→ Updated app: {app.display_name}")
                )
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Done! Created {created_count} apps, updated {updated_count} apps."
            )
        )
        self.stdout.write("\nNext steps:")
        self.stdout.write("1. Go to Django Admin → Users")
        self.stdout.write('2. Edit a user and assign apps in the "App Access" section')
        self.stdout.write(
            '3. Use "System Permissions" to control add/view/change/delete within those apps'
        )
