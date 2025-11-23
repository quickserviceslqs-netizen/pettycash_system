"""
Currency formatting utilities using system settings
"""
from decimal import Decimal
from settings_manager.models import get_setting


def format_currency(amount, currency_code=None, include_symbol=True):
    """
    Format a currency amount according to system settings
    
    Args:
        amount: Numeric amount to format (can be int, float, Decimal, or string)
        currency_code: Optional currency code override (defaults to system setting)
        include_symbol: Whether to include currency symbol (default: True)
    
    Returns:
        Formatted currency string
    
    Example:
        >>> format_currency(1234567.89)
        'KSh 1,234,567.89'
        >>> format_currency(1000, currency_code='USD')
        '$ 1,000.00'
        >>> format_currency(500.5, include_symbol=False)
        '500.50'
    """
    try:
        # Convert to Decimal for precise calculations
        if isinstance(amount, str):
            amount = Decimal(amount)
        elif isinstance(amount, (int, float)):
            amount = Decimal(str(amount))
        elif not isinstance(amount, Decimal):
            amount = Decimal('0')
    except (ValueError, TypeError):
        amount = Decimal('0')
    
    # Get formatting settings
    decimal_places = int(get_setting('CURRENCY_DECIMAL_PLACES', '2'))
    thousand_sep = get_setting('CURRENCY_THOUSAND_SEPARATOR', ',')
    decimal_sep = get_setting('CURRENCY_DECIMAL_SEPARATOR', '.')
    symbol_position = get_setting('CURRENCY_SYMBOL_POSITION', 'before')
    
    # Get currency symbol
    if currency_code:
        symbol = get_currency_symbol(currency_code)
    else:
        symbol = get_setting('CURRENCY_SYMBOL', 'KSh')
    
    # Round to specified decimal places
    format_str = f'{{:,.{decimal_places}f}}'
    formatted = format_str.format(amount)
    
    # Replace separators if custom ones are specified
    if thousand_sep != ',':
        formatted = formatted.replace(',', '|TEMP|')
        formatted = formatted.replace('.', decimal_sep)
        formatted = formatted.replace('|TEMP|', thousand_sep)
    elif decimal_sep != '.':
        formatted = formatted.replace('.', decimal_sep)
    
    # Add currency symbol if requested
    if include_symbol and symbol:
        if symbol_position == 'after':
            formatted = f'{formatted} {symbol}'
        else:  # before
            formatted = f'{symbol} {formatted}'
    
    return formatted


def get_currency_symbol(currency_code):
    """
    Get the symbol for a given currency code
    
    Args:
        currency_code: ISO 4217 currency code (e.g., 'USD', 'EUR', 'KES')
    
    Returns:
        Currency symbol string
    """
    # Common currency symbols mapping
    currency_symbols = {
        'KES': 'KSh',
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'CNY': '¥',
        'INR': '₹',
        'AUD': 'A$',
        'CAD': 'C$',
        'CHF': 'CHF',
        'ZAR': 'R',
        'NGN': '₦',
        'GHS': 'GH₵',
        'UGX': 'USh',
        'TZS': 'TSh',
        'RWF': 'FRw',
        'ETB': 'Br',
        'AED': 'د.إ',
        'SAR': 'SR',
    }
    
    return currency_symbols.get(currency_code.upper(), currency_code)


def parse_currency(currency_string):
    """
    Parse a formatted currency string back to Decimal
    
    Args:
        currency_string: Formatted currency string (e.g., 'KSh 1,234.56')
    
    Returns:
        Decimal value
    
    Example:
        >>> parse_currency('KSh 1,234.56')
        Decimal('1234.56')
        >>> parse_currency('$1,000.00')
        Decimal('1000.00')
    """
    if not currency_string:
        return Decimal('0')
    
    # Remove common currency symbols and spaces
    cleaned = str(currency_string).strip()
    for symbol in ['KSh', '$', '€', '£', '¥', '₹', 'R', '₦', 'GH₵', 'USh', 'TSh', 'FRw', 'Br']:
        cleaned = cleaned.replace(symbol, '')
    
    # Remove spaces and thousand separators
    thousand_sep = get_setting('CURRENCY_THOUSAND_SEPARATOR', ',')
    decimal_sep = get_setting('CURRENCY_DECIMAL_SEPARATOR', '.')
    
    cleaned = cleaned.replace(' ', '').replace(thousand_sep, '')
    
    # Replace decimal separator with standard period
    if decimal_sep != '.':
        cleaned = cleaned.replace(decimal_sep, '.')
    
    try:
        return Decimal(cleaned)
    except (ValueError, TypeError):
        return Decimal('0')


def get_active_currencies():
    """
    Get list of active currencies in the system
    
    Returns:
        List of currency codes
    """
    default_currency = get_setting('CURRENCY_CODE', 'KES')
    multi_currency_enabled = get_setting('ENABLE_MULTI_CURRENCY', 'false') == 'true'
    
    if not multi_currency_enabled:
        return [default_currency]
    
    # If multi-currency is enabled, return common currencies
    # This could be extended to fetch from a database table
    return [
        'KES', 'USD', 'EUR', 'GBP', 'JPY', 'CNY', 'INR',
        'AUD', 'CAD', 'ZAR', 'NGN', 'UGX', 'TZS'
    ]


def convert_currency(amount, from_currency, to_currency, exchange_rate=None):
    """
    Convert amount from one currency to another
    
    Args:
        amount: Amount to convert
        from_currency: Source currency code
        to_currency: Target currency code
        exchange_rate: Optional exchange rate (fetched if not provided)
    
    Returns:
        Converted amount as Decimal
    """
    if from_currency == to_currency:
        return Decimal(str(amount))
    
    if exchange_rate is None:
        # This would fetch from exchange rate table or API
        # For now, return the amount unchanged
        # TODO: Implement exchange rate lookup
        return Decimal(str(amount))
    
    try:
        return Decimal(str(amount)) * Decimal(str(exchange_rate))
    except (ValueError, TypeError):
        return Decimal(str(amount))


def validate_currency_code(code):
    """
    Validate if a currency code is supported
    
    Args:
        code: Currency code to validate
    
    Returns:
        Boolean indicating if code is valid
    """
    valid_codes = [
        'KES', 'USD', 'EUR', 'GBP', 'JPY', 'CNY', 'INR', 'AUD', 'CAD',
        'CHF', 'ZAR', 'NGN', 'GHS', 'UGX', 'TZS', 'RWF', 'ETB', 'AED', 'SAR'
    ]
    return code.upper() in valid_codes


# Template tag friendly wrapper
def currency(value, code=None):
    """
    Template tag friendly currency formatter
    
    Usage in templates:
        {{ amount|currency }}
        {{ amount|currency:"USD" }}
    """
    return format_currency(value, currency_code=code)
