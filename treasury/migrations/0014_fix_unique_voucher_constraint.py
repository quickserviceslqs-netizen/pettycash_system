from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('treasury', '0013_merge_20251209_1058'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'unique_voucher_number'
                    ) THEN
                        ALTER TABLE treasury_payment
                        ADD CONSTRAINT unique_voucher_number UNIQUE (voucher_number);
                    END IF;
                END $$;
            """,
            reverse_sql="""
                ALTER TABLE treasury_payment
                DROP CONSTRAINT IF EXISTS unique_voucher_number;
            """,
        ),
    ]