# M-Pesa Bulk Payment Processing Guide

## Overview
This feature allows treasury staff to efficiently process multiple approved requisitions as M-Pesa bulk payments. Treasury can review, select, and either download an Excel file for the M-Pesa portal or send payments directly to the M-Pesa API for batch processing.

## Workflow

### 1. **Select Payments for Processing**
**URL:** `/treasury/admin/bulk-payment/select/`

Treasury staff can:
- View all approved requisitions awaiting payment
- Filter by company, branch, or search by name/purpose
- Select one, few, or all payments to process
- See total count and amount before proceeding

**Features:**
- ✅ Select All / Clear All buttons
- ✅ Individual checkbox selection
- ✅ Real-time selected count and amount
- ✅ Filter by company/branch
- ✅ Search functionality

### 2. **Choose Processing Method**

After selecting payments, treasury has two options:

#### Option A: Download Excel File
- Generates M-Pesa bulk payment template in Excel format
- Auto-filled with selected requisition data
- Can be uploaded to M-Pesa portal manually
- Complies with M-Pesa format requirements

#### Option B: Send to M-Pesa API (Recommended)
- Sends payment batch directly to M-Pesa API
- Creates Payment records with status "Executing"
- M-Pesa processes all payments and sends callbacks
- Automatic status updates based on M-Pesa responses

### 3. **Review Before Submission**
**URL:** `/treasury/admin/bulk-payment/send-api/`

Before final submission, treasury reviews:
- Voucher numbers (auto-generated)
- Recipient names and phone numbers
- Payment amounts and purposes
- Company/branch information
- Total batch amount

### 4. **Batch Processing**
When submitted to M-Pesa API:
- Payment records created with unique voucher numbers
- Status set to "Executing"
- All payments sent in single API call
- M-Pesa processes batch and sends individual callbacks
- Status updated automatically per transaction

## M-Pesa Template Format

The generated Excel file contains these columns:

| Column | Description | Example |
|--------|-------------|---------|
| **MobileNumber** | Recipient phone in format 254XXXXXXXXX | 254712345678 |
| **DocumentType** | Left empty (M-Pesa allows) | |
| **DocumentNumber** | Unique voucher number | PAY123ABC456DEF7 |
| **Amount** | Payment amount | 5000 |
| **PurposeOfPayment** | Sanitized description (no special chars) | Office supplies payment |
| **Name** | Recipient full name | John Doe |

### M-Pesa Compliance
- ✅ No special characters in Purpose field (auto-sanitized)
- ✅ Phone numbers validated (must be 254XXXXXXXXX format)
- ✅ Unique voucher numbers prevent duplicates
- ✅ DocumentType can be empty

## Payment Model Updates

### New Fields Added to Payment Model

```python
# Optional requisition (bulk uploads may not have requisition)
requisition = ForeignKey(Requisition, null=True, blank=True)

# Unique voucher number for M-Pesa tracking
voucher_number = CharField(max_length=50, unique=True)

# Payment description/purpose
description = TextField(blank=True, null=True)

# Creator (for bulk uploads)
created_by = ForeignKey(User, related_name='created_payments')
```

## API Integration (Setup Required)

### Prerequisites
1. M-Pesa API credentials from Safaricom
2. Shortcode/Till number
3. Initiator name and security credential
4. Callback URLs configured

### Settings Configuration
Add to `settings.py`:
```python
# M-Pesa Configuration
MPESA_SHORTCODE = 'your_shortcode'
MPESA_INITIATOR_NAME = 'your_initiator'
MPESA_SECURITY_CREDENTIAL = 'your_credential'
MPESA_CONSUMER_KEY = 'your_consumer_key'
MPESA_CONSUMER_SECRET = 'your_consumer_secret'
MPESA_PASSKEY = 'your_passkey'

# Callback URLs
MPESA_TIMEOUT_URL = 'https://yourdomain.com/treasury/api/mpesa/timeout/'
MPESA_RESULT_URL = 'https://yourdomain.com/treasury/api/mpesa/callback/'
```

### Enable API Integration
Uncomment the API request code in `treasury/views_admin.py` in the `send_to_mpesa_api()` function:

```python
# TODO: Send to M-Pesa API
# Uncomment this section and configure settings
mpesa_response = requests.post(
    'https://api.safaricom.co.ke/mpesa/b2c/v1/paymentrequest',
    json={
        'InitiatorName': settings.MPESA_INITIATOR_NAME,
        'SecurityCredential': settings.MPESA_SECURITY_CREDENTIAL,
        'CommandID': 'BusinessPayment',
        'Amount': sum(p['Amount'] for p in payments_data),
        'PartyA': settings.MPESA_SHORTCODE,
        'Remarks': 'Bulk payment processing',
        'QueueTimeOutURL': settings.MPESA_TIMEOUT_URL,
        'ResultURL': settings.MPESA_RESULT_URL,
        'Occassion': 'Bulk Payment',
        'Transactions': payments_data,
    },
    headers={
        'Authorization': f'Bearer {get_mpesa_access_token()}',
        'Content-Type': 'application/json',
    }
)
```

## URL Routes

| Route | View | Purpose |
|-------|------|---------|
| `/treasury/admin/bulk-payment/select/` | `select_payments_for_bulk` | Select requisitions to pay |
| `/treasury/admin/bulk-payment/generate/` | `generate_mpesa_bulk` | Download Excel template |
| `/treasury/admin/bulk-payment/send-api/` | `send_to_mpesa_api` | Send to M-Pesa API |
| `/treasury/admin/bulk-payment/upload/` | `bulk_payment_upload` | Manual file upload (alternative) |
| `/treasury/admin/bulk-payment/process/` | `process_bulk_payments` | Process uploaded file |

## Permissions Required

- `treasury.can_manage_payments` - Required for all bulk payment operations

## Security Features

1. **Unique Voucher Numbers** - Prevents duplicate payments
2. **Phone Validation** - Ensures valid Kenyan mobile numbers
3. **Special Character Sanitization** - M-Pesa compliance
4. **Duplicate Detection** - Checks existing voucher numbers
5. **Permission Checks** - Only authorized treasury staff
6. **Audit Trail** - Tracks who created payments (created_by field)

## User Experience Flow

```
Treasury Dashboard
    ↓
Select Payments for Bulk Processing
    ↓
[Filter by company/branch/search]
    ↓
[Select one, few, or all]
    ↓
Choose Processing Method:
    ├─→ Download Excel File → Manual upload to M-Pesa portal
    └─→ Send to M-Pesa API → Review → Confirm → Batch processing
                                           ↓
                                    M-Pesa processes batch
                                           ↓
                                    Callbacks update status
                                           ↓
                                    View results in Payments
```

## Benefits

1. **Efficiency** - Process multiple payments in one action
2. **Accuracy** - Auto-fill from approved requisitions
3. **Flexibility** - Choose between Excel download or API submission
4. **Compliance** - Automatic M-Pesa format validation
5. **Tracking** - Unique voucher numbers for reconciliation
6. **Control** - Treasury decides which payments to process
7. **Scalability** - Handle large payment batches easily

## Future Enhancements

- [ ] Payment status dashboard
- [ ] Failed payment retry mechanism
- [ ] Payment reconciliation report
- [ ] Email notifications on batch completion
- [ ] Payment scheduling (future dates)
- [ ] Multi-currency support
- [ ] Bank transfer bulk processing
- [ ] Payment approval workflow for large batches

## Support

For issues or questions:
1. Check M-Pesa API documentation
2. Verify phone number formats
3. Review callback URL configuration
4. Check Payment model for status updates
5. Monitor Django logs for API errors
