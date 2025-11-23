"""
Template tags for currency formatting and system settings access
"""
from django import template
from settings_manager.currency_utils import format_currency, get_currency_symbol
from settings_manager.models import get_setting

register = template.Library()


@register.filter(name='currency')
def currency_filter(value, currency_code=None):
    """
    Format a number as currency according to system settings
    
    Usage:
        {{ amount|currency }}
        {{ amount|currency:"USD" }}
        {{ 1234.56|currency }}  -> "KSh 1,234.56"
    """
    return format_currency(value, currency_code=currency_code)


@register.filter(name='currency_nosymbol')
def currency_nosymbol_filter(value):
    """
    Format a number as currency without symbol
    
    Usage:
        {{ amount|currency_nosymbol }}
        {{ 1234.56|currency_nosymbol }}  -> "1,234.56"
    """
    return format_currency(value, include_symbol=False)


@register.simple_tag
def get_system_setting(key, default=''):
    """
    Get a system setting value in templates
    
    Usage:
        {% get_system_setting 'CURRENCY_CODE' %}
        {% get_system_setting 'APPROVAL_THRESHOLD_LEVEL_1' '10000' %}
    """
    return get_setting(key, default)


@register.simple_tag
def currency_symbol(code=None):
    """
    Get currency symbol for display
    
    Usage:
        {% currency_symbol %}  -> "KSh" (default currency)
        {% currency_symbol "USD" %}  -> "$"
    """
    if code:
        return get_currency_symbol(code)
    return get_setting('CURRENCY_SYMBOL', 'KSh')


@register.filter(name='format_amount')
def format_amount(value, decimals=2):
    """
    Format a number with thousand separators
    
    Usage:
        {{ value|format_amount }}
        {{ value|format_amount:0 }}  -> no decimals
    """
    try:
        thousand_sep = get_setting('CURRENCY_THOUSAND_SEPARATOR', ',')
        decimal_sep = get_setting('CURRENCY_DECIMAL_SEPARATOR', '.')
        
        format_str = f'{{:,.{decimals}f}}'
        formatted = format_str.format(float(value))
        
        if thousand_sep != ',':
            formatted = formatted.replace(',', '|TEMP|')
            formatted = formatted.replace('.', decimal_sep)
            formatted = formatted.replace('|TEMP|', thousand_sep)
        elif decimal_sep != '.':
            formatted = formatted.replace('.', decimal_sep)
        
        return formatted
    except (ValueError, TypeError):
        return value


@register.inclusion_tag('settings_manager/currency_display.html')
def display_currency(amount, label='', currency_code=None, css_class=''):
    """
    Display currency with optional label in a consistent format
    
    Usage:
        {% display_currency amount "Total:" %}
        {% display_currency payment.amount "Paid:" "USD" "text-success" %}
    """
    return {
        'amount': amount,
        'label': label,
        'formatted': format_currency(amount, currency_code=currency_code),
        'css_class': css_class,
    }


@register.simple_tag
def setting_enabled(key):
    """
    Check if a boolean setting is enabled
    
    Usage:
        {% setting_enabled 'ENABLE_MULTI_CURRENCY' %}
    """
    return get_setting(key, 'false').lower() in ['true', '1', 'yes', 'on']
