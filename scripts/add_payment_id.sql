-- Add a nullable UUID `payment_id` column to `treasury_payment` and backfill values.
-- Run this in Postgres BEFORE attempting to apply Django migration `treasury.0002_phase6_dashboard_models`.
-- IMPORTANT: Take a full backup before running.

BEGIN;

-- Ensure uuid extension available (try pgcrypto then uuid-ossp)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto') THEN
        BEGIN
            CREATE EXTENSION IF NOT EXISTS pgcrypto;
        EXCEPTION WHEN others THEN
            -- ignore if cannot create; next we try uuid-ossp
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

-- Add column if not exists
ALTER TABLE treasury_payment
    ADD COLUMN IF NOT EXISTS payment_id uuid;

-- Backfill values using gen_random_uuid() if available, else uuid_generate_v4()
UPDATE treasury_payment
SET payment_id = COALESCE(payment_id,
    (CASE
        WHEN (SELECT COUNT(*) FROM pg_extension WHERE extname = 'pgcrypto') > 0 THEN gen_random_uuid()
        WHEN (SELECT COUNT(*) FROM pg_extension WHERE extname = 'uuid-ossp') > 0 THEN uuid_generate_v4()
        ELSE NULL
    END)
);

-- If values are still NULL (no extension), provide a warning to manually set UUIDs
-- Optionally add a unique index (recommended)
CREATE UNIQUE INDEX IF NOT EXISTS idx_treasury_payment_payment_id ON treasury_payment(payment_id);

COMMIT;

-- After running this script, verify the column exists and is populated, then re-run `python manage.py migrate` to apply `0002`.
