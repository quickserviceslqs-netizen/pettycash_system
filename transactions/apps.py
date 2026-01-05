from django.apps import AppConfig


class TransactionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "transactions"

    def ready(self):
        # Import signals only if not during migrations
        try:
            from django.db import connection
            # Check if migrations table exists
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM django_migrations LIMIT 1")
            import transactions.signals  # ensure signals are registered
        except Exception:
            # Skip during migrations
            pass
