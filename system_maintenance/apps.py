from django.apps import AppConfig


class SystemMaintenanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "system_maintenance"

    def ready(self):
        """Import signals when app is ready"""
        import system_maintenance.signals  # noqa
