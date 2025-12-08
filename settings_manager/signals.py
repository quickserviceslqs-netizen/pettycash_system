"""
Signals for settings_manager app
Clear cache when settings are modified
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import SystemSetting


@receiver(post_save, sender=SystemSetting)
def clear_setting_cache_on_save(sender, instance, **kwargs):
    """Clear cache when a setting is saved"""
    cache_key = f'system_setting:{instance.key}'
    cache.delete(cache_key)


@receiver(post_delete, sender=SystemSetting)
def clear_setting_cache_on_delete(sender, instance, **kwargs):
    """Clear cache when a setting is deleted"""
    cache_key = f'system_setting:{instance.key}'
    cache.delete(cache_key)
