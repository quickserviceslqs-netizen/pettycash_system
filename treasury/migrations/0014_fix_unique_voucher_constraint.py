from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("treasury", "0013_merge_20251209_1058"),
    ]

    operations = [
        migrations.RunPython(
            code=lambda apps, schema_editor: (
                schema_editor.execute("""
                    ALTER TABLE treasury_payment
                    ADD CONSTRAINT unique_voucher_number UNIQUE (voucher_number);
                """)
                if schema_editor.connection.vendor == "postgresql"
                else print("Non-postgres DB detected: skipping unique_voucher_number constraint addition")
            ),
            reverse_code=lambda apps, schema_editor: (
                schema_editor.execute("""
                    ALTER TABLE treasury_payment
                    DROP CONSTRAINT IF EXISTS unique_voucher_number;
                """)
                if schema_editor.connection.vendor == "postgresql"
                else print("Non-postgres DB detected: skipping unique_voucher_number constraint drop")
            ),
        ),
    ]
