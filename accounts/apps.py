from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        # Import signal handlers only if not during migrations
        try:
            from django.db import connection
            # Check if migrations table exists (indicates DB is set up)
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM django_migrations LIMIT 1")
            import accounts.signals  # noqa: F401
        except Exception:
            # Avoid crashing on migrations when dependencies are not ready
            pass
