from django.apps import AppConfig


class SettingsManagerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "settings_manager"

    def ready(self):
        """Register signals when app is ready"""
        import settings_manager.signals
