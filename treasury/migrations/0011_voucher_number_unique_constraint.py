from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('treasury', '0010_payment_fields_safe_add'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='payment',
            constraint=models.UniqueConstraint(fields=['voucher_number'], name='unique_voucher_number'),
        ),
    ]
