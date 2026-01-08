from django.apps import AppConfig


class SystemMaintenanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "system_maintenance"

    def ready(self):
        """Import signals when app is ready, but skip during migrations"""
        try:
            from django.db import connection
            # Check if migrations table exists
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM django_migrations LIMIT 1")
            import system_maintenance.signals  # noqa
        except Exception:
            # Skip during migrations
            pass
