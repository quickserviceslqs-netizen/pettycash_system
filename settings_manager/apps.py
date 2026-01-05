from django.apps import AppConfig


class SettingsManagerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "settings_manager"

    def ready(self):
        # Register signals only if not during migrations
        try:
            from django.db import connection
            # Check if migrations table exists
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM django_migrations LIMIT 1")
            import settings_manager.signals
        except Exception:
            # Skip during migrations
            pass
