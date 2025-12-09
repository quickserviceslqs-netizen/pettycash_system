"""
Template tags for currency formatting using system settings
"""

from django import template
from settings_manager.currency_utils import format_currency as format_currency_util

register = template.Library()


@register.filter(name="currency")
def currency(value, currency_code=None):
    """
    Format a value as currency using system settings

    Usage:
        {{ amount|currency }}
        {{ amount|currency:"USD" }}
    """
    if value is None:
        return ""
    return format_currency_util(value, currency_code=currency_code)


@register.filter(name="currency_nosymbol")
def currency_nosymbol(value):
    """
    Format a value as currency without symbol

    Usage:
        {{ amount|currency_nosymbol }}
    """
    if value is None:
        return ""
    return format_currency_util(value, include_symbol=False)


@register.simple_tag
def currency_symbol():
    """
    Get the current currency symbol from settings

    Usage:
        {% currency_symbol %}
    """
    from settings_manager.models import get_setting

    return get_setting("CURRENCY_SYMBOL", "KSh")


@register.simple_tag
def currency_code():
    """
    Get the current currency code from settings

    Usage:
        {% currency_code %}
    """
    from settings_manager.models import get_setting

    return get_setting("CURRENCY_CODE", "KES")
