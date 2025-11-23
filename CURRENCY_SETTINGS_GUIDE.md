# Currency Settings Documentation

## Overview
The petty cash system now includes comprehensive currency configuration settings that allow you to customize how monetary values are displayed and processed throughout the application.

## Currency Settings (12 Total in General Category)

### 1. **CURRENCY_CODE**
- **Display Name**: Default Currency Code
- **Type**: String
- **Default**: `KES`
- **Description**: ISO 4217 currency code for all transactions
- **Examples**: KES, USD, EUR, GBP, JPY, CNY, INR, AUD, CAD, ZAR, NGN, UGX, TZS

### 2. **CURRENCY_SYMBOL** ⭐ NEW
- **Display Name**: Currency Symbol
- **Type**: String
- **Default**: `KSh`
- **Description**: Symbol displayed for the currency
- **Examples**: KSh, $, €, £, ¥, ₹, R, ₦

### 3. **CURRENCY_SYMBOL_POSITION** ⭐ NEW
- **Display Name**: Currency Symbol Position
- **Type**: String
- **Default**: `before`
- **Description**: Where to place the currency symbol relative to the amount
- **Options**: 
  - `before` → "KSh 1,234.56"
  - `after` → "1,234.56 KSh"

### 4. **CURRENCY_DECIMAL_PLACES** ⭐ NEW
- **Display Name**: Currency Decimal Places
- **Type**: Integer
- **Default**: `2`
- **Description**: Number of decimal places to display
- **Examples**: 
  - `2` → 1,234.56
  - `0` → 1,235
  - `3` → 1,234.560

### 5. **CURRENCY_THOUSAND_SEPARATOR** ⭐ NEW
- **Display Name**: Thousand Separator
- **Type**: String
- **Default**: `,` (comma)
- **Description**: Character used to separate thousands
- **Examples**:
  - `,` → 1,234,567.89
  - `.` → 1.234.567,89 (European style)
  - ` ` → 1 234 567.89 (space)

### 6. **CURRENCY_DECIMAL_SEPARATOR** ⭐ NEW
- **Display Name**: Decimal Separator
- **Type**: String
- **Default**: `.` (period)
- **Description**: Character used as decimal point
- **Examples**:
  - `.` → 1,234.56
  - `,` → 1.234,56 (European style)

### 7. **ENABLE_MULTI_CURRENCY** ⭐ NEW
- **Display Name**: Enable Multi-Currency Support
- **Type**: Boolean
- **Default**: `false`
- **Description**: Allow transactions in multiple currencies with exchange rates
- **When enabled**: Users can select different currencies for transactions

### 8. **EXCHANGE_RATE_AUTO_UPDATE** ⭐ NEW
- **Display Name**: Auto-Update Exchange Rates
- **Type**: Boolean
- **Default**: `false`
- **Description**: Automatically fetch current exchange rates from external API
- **Requires**: `EXCHANGE_RATE_API_KEY` to be set

### 9. **EXCHANGE_RATE_API_KEY** ⭐ NEW
- **Display Name**: Exchange Rate API Key
- **Type**: String (Sensitive)
- **Default**: Empty
- **Description**: API key for exchange rate service
- **Suggested Services**: 
  - exchangerate-api.com
  - fixer.io
  - openexchangerates.org
- **Security**: Marked as sensitive, value hidden in UI

### Other General Settings
10. **DATE_FORMAT** - Date display format (Y-m-d)
11. **ITEMS_PER_PAGE** - Pagination setting (20)
12. **MAINTENANCE_MODE** - System maintenance toggle (false)

## Currency Formatting Examples

### Default Format (KES - Kenyan Shilling)
```
Amount: 1234567.89
Formatted: KSh 1,234,567.89
```

### USD Format
```
Currency Code: USD
Symbol: $
Position: before
Result: $ 1,234,567.89
```

### European Format (EUR)
```
Currency Code: EUR
Symbol: €
Thousand Separator: . (period)
Decimal Separator: , (comma)
Position: before
Result: € 1.234.567,89
```

### Japanese Yen (No Decimals)
```
Currency Code: JPY
Symbol: ¥
Decimal Places: 0
Result: ¥ 1,234,568
```

## Using Currency Formatting in Code

### Python Code

```python
from settings_manager.currency_utils import format_currency

# Basic usage
amount = 1234.56
formatted = format_currency(amount)  # "KSh 1,234.56"

# With specific currency
formatted_usd = format_currency(amount, currency_code='USD')  # "$ 1,234.56"

# Without symbol
formatted_plain = format_currency(amount, include_symbol=False)  # "1,234.56"

# Parse currency string back to number
from settings_manager.currency_utils import parse_currency
value = parse_currency("KSh 1,234.56")  # Decimal('1234.56')
```

### Django Templates

First, load the template tags:
```django
{% load settings_tags %}
```

Then use the filters:
```django
<!-- Format as currency -->
{{ payment.amount|currency }}
<!-- Output: KSh 1,234.56 -->

<!-- Format with specific currency -->
{{ payment.amount|currency:"USD" }}
<!-- Output: $ 1,234.56 -->

<!-- Format without symbol -->
{{ payment.amount|currency_nosymbol }}
<!-- Output: 1,234.56 -->

<!-- Using inclusion tag for consistent display -->
{% display_currency payment.amount "Total Payment:" %}

<!-- Get system setting value -->
{% get_system_setting 'CURRENCY_CODE' %}
<!-- Output: KES -->

<!-- Get currency symbol -->
{% currency_symbol %}
<!-- Output: KSh -->

<!-- Check if setting is enabled -->
{% setting_enabled 'ENABLE_MULTI_CURRENCY' %}
<!-- Output: True or False -->
```

## Currency Utilities Functions

### `format_currency(amount, currency_code=None, include_symbol=True)`
Formats a numeric amount according to system settings.

### `get_currency_symbol(currency_code)`
Returns the symbol for a given currency code.

### `parse_currency(currency_string)`
Parses a formatted currency string back to a Decimal value.

### `get_active_currencies()`
Returns list of active currency codes in the system.

### `convert_currency(amount, from_currency, to_currency, exchange_rate=None)`
Converts amount between currencies (requires exchange rate).

### `validate_currency_code(code)`
Checks if a currency code is supported.

## Supported Currencies

The system includes symbols for these currencies:
- **KES** - Kenyan Shilling (KSh)
- **USD** - US Dollar ($)
- **EUR** - Euro (€)
- **GBP** - British Pound (£)
- **JPY** - Japanese Yen (¥)
- **CNY** - Chinese Yuan (¥)
- **INR** - Indian Rupee (₹)
- **AUD** - Australian Dollar (A$)
- **CAD** - Canadian Dollar (C$)
- **CHF** - Swiss Franc (CHF)
- **ZAR** - South African Rand (R)
- **NGN** - Nigerian Naira (₦)
- **GHS** - Ghanaian Cedi (GH₵)
- **UGX** - Ugandan Shilling (USh)
- **TZS** - Tanzanian Shilling (TSh)
- **RWF** - Rwandan Franc (FRw)
- **ETB** - Ethiopian Birr (Br)
- **AED** - UAE Dirham (د.إ)
- **SAR** - Saudi Riyal (SR)

## Multi-Currency Support

When `ENABLE_MULTI_CURRENCY` is enabled:
1. Users can select currency for each transaction
2. Exchange rates can be managed manually or auto-updated
3. Reports can show amounts in multiple currencies
4. System maintains default currency for accounting

### Setting Up Multi-Currency

1. **Enable Multi-Currency**
   ```
   Settings → General → Enable Multi-Currency Support → true
   ```

2. **Configure Exchange Rate Updates** (Optional)
   ```
   Settings → General → Auto-Update Exchange Rates → true
   Settings → General → Exchange Rate API Key → [Your API Key]
   ```

3. **Supported Services**:
   - **exchangerate-api.com**: Free tier available, easy setup
   - **fixer.io**: Reliable, paid service
   - **openexchangerates.org**: Free and paid tiers

## Configuration Examples

### Example 1: Standard Kenyan Setup
```
CURRENCY_CODE: KES
CURRENCY_SYMBOL: KSh
CURRENCY_SYMBOL_POSITION: before
CURRENCY_DECIMAL_PLACES: 2
CURRENCY_THOUSAND_SEPARATOR: ,
CURRENCY_DECIMAL_SEPARATOR: .
Result: KSh 1,234,567.89
```

### Example 2: US Dollar Setup
```
CURRENCY_CODE: USD
CURRENCY_SYMBOL: $
CURRENCY_SYMBOL_POSITION: before
CURRENCY_DECIMAL_PLACES: 2
CURRENCY_THOUSAND_SEPARATOR: ,
CURRENCY_DECIMAL_SEPARATOR: .
Result: $ 1,234,567.89
```

### Example 3: European (French) Setup
```
CURRENCY_CODE: EUR
CURRENCY_SYMBOL: €
CURRENCY_SYMBOL_POSITION: after
CURRENCY_DECIMAL_PLACES: 2
CURRENCY_THOUSAND_SEPARATOR: (space)
CURRENCY_DECIMAL_SEPARATOR: ,
Result: 1 234 567,89 €
```

### Example 4: Japanese Yen Setup
```
CURRENCY_CODE: JPY
CURRENCY_SYMBOL: ¥
CURRENCY_SYMBOL_POSITION: before
CURRENCY_DECIMAL_PLACES: 0
CURRENCY_THOUSAND_SEPARATOR: ,
CURRENCY_DECIMAL_SEPARATOR: .
Result: ¥ 1,234,568
```

## Best Practices

1. **Test Format Changes**: Preview currency display before changing settings
2. **Backup Before Changes**: Export settings before major currency changes
3. **Consistent Formatting**: Use template tags for consistent display throughout app
4. **Decimal Precision**: Match decimal places to currency standard (0 for JPY, 2 for most)
5. **API Security**: Store exchange rate API keys securely (marked as sensitive)
6. **Multi-Currency**: Only enable if needed, adds complexity

## Accessing Settings

### Via Settings Manager UI
1. Navigate to **Settings** (top navigation)
2. Click on **General Settings** category card
3. Find currency-related settings
4. Click **Edit** icon to modify values
5. Changes take effect immediately (no restart required)

### Via Django Admin
1. Go to `/admin/settings_manager/systemsetting/`
2. Filter by category: "general"
3. Edit currency settings directly

### Via Code
```python
from settings_manager.models import get_setting

currency_code = get_setting('CURRENCY_CODE', 'KES')
symbol = get_setting('CURRENCY_SYMBOL', 'KSh')
decimals = int(get_setting('CURRENCY_DECIMAL_PLACES', '2'))
```

## Troubleshooting

### Currency Not Formatting Correctly
- Check `CURRENCY_THOUSAND_SEPARATOR` and `CURRENCY_DECIMAL_SEPARATOR` settings
- Verify `CURRENCY_DECIMAL_PLACES` is appropriate for your currency
- Clear browser cache after changing settings

### Symbol Not Displaying
- Ensure `CURRENCY_SYMBOL` is set correctly
- Check HTML encoding supports special characters (€, £, ¥, ₹, etc.)
- Verify template includes `{% load settings_tags %}`

### Multi-Currency Not Working
- Verify `ENABLE_MULTI_CURRENCY` is set to `true`
- Check exchange rate table has entries
- Ensure `EXCHANGE_RATE_API_KEY` is valid if using auto-update

## Future Enhancements

Potential future additions:
- Currency conversion history tracking
- Real-time exchange rate display
- Multi-currency reporting dashboards
- Currency-specific rounding rules
- Cryptocurrency support
- Historical exchange rate charts
- Bulk currency conversion tools

## Related Settings

These settings work together with currency formatting:
- **DATE_FORMAT** - Consistent date/currency display
- **ITEMS_PER_PAGE** - Affects report pagination with currency totals
- **Report Export Formats** - Currency formatting in exports
- **Payment Settings** - Payment limits use currency formatting

## Activity Logging

All currency setting changes are logged in the Activity Logs:
- Who changed the setting
- When it was changed
- Old and new values
- IP address and user agent

Access logs at: **Settings → Activity Logs**
