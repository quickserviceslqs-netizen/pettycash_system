# Render Deployment Fix for Migration Error

## Issue
Migration `0009_payment_created_by_payment_description_and_more` fails with:
```
django.db.utils.ProgrammingError: column "created_by_id" of relation "treasury_payment" already exists
```

## Solution
The migration has been replaced with a safe version (`0010_payment_fields_safe_add.py`) that checks if columns exist before attempting to add them.

## What Changed

### Old Migration (Removed)
- `treasury/migrations/0009_payment_created_by_payment_description_and_more.py` - DELETED

### New Migration (Safe Version)
- `treasury/migrations/0010_payment_fields_safe_add.py` - Uses RunPython to check column existence

## How It Works

The new migration:
1. Queries `information_schema.columns` to check which columns already exist
2. Only adds columns that don't exist:
   - `created_by_id` (if missing)
   - `description` (if missing)
   - `voucher_number` (if missing)
3. Makes `requisition_id` nullable if it isn't already

## Render Deployment Steps

### If Migration 0009 Already Applied Partially
1. The new migration 0010 will detect existing columns and skip them
2. Deploy will complete successfully
3. No manual intervention needed

### If Migration 0009 Failed Completely
1. Mark migration 0009 as fake (it's been removed from code):
   ```bash
   python manage.py migrate treasury 0008
   ```
2. Deploy new code with migration 0010
3. Migration 0010 will run and add only missing columns

### Manual Database Fix (If Needed)
If you need to manually fix the database state:

```sql
-- Check migration status
SELECT * FROM django_migrations WHERE app = 'treasury' ORDER BY applied DESC LIMIT 5;

-- If 0009 is listed but failed, remove it
DELETE FROM django_migrations WHERE app = 'treasury' AND name = '0009_payment_created_by_payment_description_and_more';

-- Then run migrations normally
```

## Verification

After deployment, verify the Payment model has all required fields:

```sql
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'treasury_payment' 
AND column_name IN ('created_by_id', 'description', 'voucher_number', 'requisition_id');
```

Expected result:
```
column_name      | data_type         | is_nullable
-----------------|-------------------|------------
created_by_id    | integer           | YES
description      | text              | YES
voucher_number   | character varying | YES
requisition_id   | uuid              | YES
```

## Commits
- `4708514` - Added safe migration 0010
- `acbdde2` - Removed problematic migration 0009

## No Data Loss
This fix is safe and will not cause any data loss. It only adds new nullable columns and makes existing columns nullable where needed.
