# Generated migration to add otp_hash field to Payment

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('treasury', '0003_phase6_dashboard_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='otp_hash',
            field=models.CharField(blank=True, help_text='SHA-256 hash of OTP', max_length=64, null=True),
        ),
    ]
