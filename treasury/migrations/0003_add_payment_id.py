from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('treasury', '0002_phase6_dashboard_models'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
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
""",
            reverse_sql="""
DROP INDEX IF EXISTS idx_treasury_payment_payment_id;
ALTER TABLE treasury_payment DROP COLUMN IF EXISTS payment_id;
""",
        ),
    ]
