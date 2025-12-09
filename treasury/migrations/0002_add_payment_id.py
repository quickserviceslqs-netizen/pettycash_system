from django.db import migrations, connection


def add_payment_id_forward(apps, schema_editor):
    """Add payment_id column with UUID values"""
    db_vendor = connection.vendor

    if db_vendor == "postgresql":
        # PostgreSQL-specific SQL
        schema_editor.execute(
            """
-- Ensure uuid extension exists (try pgcrypto then uuid-ossp)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto') THEN
        BEGIN
            CREATE EXTENSION IF NOT EXISTS pgcrypto;
        EXCEPTION WHEN others THEN
            NULL;
        END;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp') THEN
        BEGIN
            CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        EXCEPTION WHEN others THEN
            NULL;
        END;
    END IF;
END$$;

-- Add nullable UUID column if not exists
ALTER TABLE treasury_payment
    ADD COLUMN IF NOT EXISTS payment_id uuid;

-- Backfill using gen_random_uuid() (pgcrypto) or uuid_generate_v4()
UPDATE treasury_payment
SET payment_id = COALESCE(payment_id,
    (CASE
        WHEN (SELECT COUNT(*) FROM pg_extension WHERE extname = 'pgcrypto') > 0 THEN gen_random_uuid()
        WHEN (SELECT COUNT(*) FROM pg_extension WHERE extname = 'uuid-ossp') > 0 THEN uuid_generate_v4()
        ELSE NULL
    END)
)
WHERE payment_id IS NULL;

-- Add a unique index if not exists
CREATE UNIQUE INDEX IF NOT EXISTS idx_treasury_payment_payment_id ON treasury_payment(payment_id);
"""
        )
    elif db_vendor == "sqlite":
        # SQLite doesn't have UUID extension, but Payment model already has payment_id as UUIDField with default
        # So we just need to ensure the column exists - Django will handle UUID generation
        pass  # Django's schema editor will create the column from the model
    else:
        raise NotImplementedError(f"Migration not supported for {db_vendor}")


def add_payment_id_reverse(apps, schema_editor):
    """Remove payment_id column"""
    db_vendor = connection.vendor

    if db_vendor == "postgresql":
        schema_editor.execute(
            """
DROP INDEX IF EXISTS idx_treasury_payment_payment_id;
ALTER TABLE treasury_payment DROP COLUMN IF EXISTS payment_id;
"""
        )
    elif db_vendor == "sqlite":
        pass  # Django will handle column removal
    else:
        raise NotImplementedError(f"Migration reversal not supported for {db_vendor}")


class Migration(migrations.Migration):
    dependencies = [
        ("treasury", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_payment_id_forward, add_payment_id_reverse),
    ]
