# Generated migration for Phase 6 models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('treasury', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TreasuryDashboard',
            fields=[
                ('dashboard_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('total_funds', models.IntegerField(default=0)),
                ('total_balance', models.DecimalField(decimal_places=2, default='0.00', max_digits=16)),
                ('total_utilization_pct', models.DecimalField(decimal_places=2, default='0.00', max_digits=5)),
                ('funds_below_reorder', models.IntegerField(default=0)),
                ('funds_critical', models.IntegerField(default=0)),
                ('payments_today', models.IntegerField(default=0)),
                ('payments_this_week', models.IntegerField(default=0)),
                ('payments_this_month', models.IntegerField(default=0)),
                ('total_amount_today', models.DecimalField(decimal_places=2, default='0.00', max_digits=14)),
                ('total_amount_this_week', models.DecimalField(decimal_places=2, default='0.00', max_digits=14)),
                ('total_amount_this_month', models.DecimalField(decimal_places=2, default='0.00', max_digits=14)),
                ('active_alerts', models.IntegerField(default=0)),
                ('critical_alerts', models.IntegerField(default=0)),
                ('pending_replenishments', models.IntegerField(default=0)),
                ('pending_replenishment_amount', models.DecimalField(decimal_places=2, default='0.00', max_digits=14)),
                ('pending_variances', models.IntegerField(default=0)),
                ('pending_variance_amount', models.DecimalField(decimal_places=2, default='0.00', max_digits=14)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('calculated_at', models.DateTimeField()),
                ('branch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='organization.branch')),
                ('company', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='treasury_dashboard', to='organization.company')),
                ('region', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='organization.region')),
            ],
            options={
                'verbose_name': 'Treasury Dashboard',
                'verbose_name_plural': 'Treasury Dashboards',
            },
        ),
        migrations.CreateModel(
            name='DashboardMetric',
            fields=[
                ('metric_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('metric_type', models.CharField(choices=[('fund_balance', 'Fund Balance'), ('payment_volume', 'Payment Volume'), ('payment_amount', 'Payment Amount'), ('utilization', 'Fund Utilization %'), ('variance_count', 'Variance Count'), ('alerts_count', 'Alerts Count')], max_length=50)),
                ('metric_date', models.DateField()),
                ('metric_hour', models.IntegerField(blank=True, null=True)),
                ('value', models.DecimalField(decimal_places=2, max_digits=16)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('dashboard', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='metrics', to='treasury.treasurydashboard')),
            ],
            options={
                'verbose_name': 'Dashboard Metric',
                'verbose_name_plural': 'Dashboard Metrics',
            },
        ),
        migrations.CreateModel(
            name='Alert',
            fields=[
                ('alert_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('alert_type', models.CharField(choices=[('fund_critical', 'Fund Balance Critical'), ('fund_low', 'Fund Balance Low'), ('payment_failed', 'Payment Failed'), ('payment_timeout', 'Payment Timeout'), ('otp_expired', 'OTP Expired'), ('variance_pending', 'Variance Pending'), ('replenishment_auto', 'Replenishment Auto-triggered'), ('execution_delay', 'Execution Delay'), ('system_error', 'System Error')], max_length=50)),
                ('severity', models.CharField(choices=[('Critical', 'Critical'), ('High', 'High'), ('Medium', 'Medium'), ('Low', 'Low')], max_length=20)),
                ('title', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('acknowledged_at', models.DateTimeField(blank=True, null=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('resolution_notes', models.TextField(blank=True, null=True)),
                ('email_sent', models.BooleanField(default=False)),
                ('email_sent_at', models.DateTimeField(blank=True, null=True)),
                ('acknowledged_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='acknowledged_alerts', to=settings.AUTH_USER_MODEL)),
                ('related_payment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='alerts', to='treasury.payment')),
                ('related_fund', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='alerts', to='treasury.treasuryfund')),
                ('related_variance', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='alerts', to='treasury.varianceadjustment')),
                ('resolved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resolved_alerts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Alert',
                'verbose_name_plural': 'Alerts',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PaymentTracking',
            fields=[
                ('tracking_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('otp_sent_at', models.DateTimeField(blank=True, null=True)),
                ('otp_verified_at', models.DateTimeField(blank=True, null=True)),
                ('execution_started_at', models.DateTimeField(blank=True, null=True)),
                ('execution_completed_at', models.DateTimeField(blank=True, null=True)),
                ('reconciliation_started_at', models.DateTimeField(blank=True, null=True)),
                ('reconciliation_completed_at', models.DateTimeField(blank=True, null=True)),
                ('total_execution_time', models.DurationField(blank=True, null=True)),
                ('otp_verification_time', models.DurationField(blank=True, null=True)),
                ('current_status', models.CharField(choices=[('created', 'Created'), ('otp_sent', 'OTP Sent'), ('otp_verified', 'OTP Verified'), ('executing', 'Executing'), ('success', 'Success'), ('failed', 'Failed'), ('reconciled', 'Reconciled')], default='created', max_length=50)),
                ('status_message', models.TextField(blank=True, null=True)),
                ('payment', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='tracking', to='treasury.payment')),
            ],
            options={
                'verbose_name': 'Payment Tracking',
                'verbose_name_plural': 'Payment Tracking',
            },
        ),
        migrations.CreateModel(
            name='FundForecast',
            fields=[
                ('forecast_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('forecast_date', models.DateField()),
                ('predicted_balance', models.DecimalField(decimal_places=2, max_digits=14)),
                ('predicted_utilization_pct', models.DecimalField(decimal_places=2, max_digits=5)),
                ('predicted_daily_expense', models.DecimalField(decimal_places=2, max_digits=14)),
                ('days_until_reorder', models.IntegerField()),
                ('needs_replenishment', models.BooleanField(default=False)),
                ('recommended_replenishment_amount', models.DecimalField(decimal_places=2, default='0.00', max_digits=14)),
                ('confidence_level', models.DecimalField(decimal_places=2, max_digits=5)),
                ('calculated_at', models.DateTimeField()),
                ('forecast_horizon_days', models.IntegerField()),
                ('fund', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='forecasts', to='treasury.treasuryfund')),
            ],
            options={
                'verbose_name': 'Fund Forecast',
                'verbose_name_plural': 'Fund Forecasts',
                'unique_together': {('fund', 'forecast_date')},
            },
        ),
        migrations.AddIndex(
            model_name='dashboardmetric',
            index=models.Index(fields=['dashboard', 'metric_type', 'metric_date'], name='treasury_da_dashboa_idx'),
        ),
        migrations.AddIndex(
            model_name='dashboardmetric',
            index=models.Index(fields=['metric_type', 'metric_date'], name='treasury_da_metric__idx'),
        ),
        migrations.AddIndex(
            model_name='alert',
            index=models.Index(fields=['alert_type', 'severity', 'created_at'], name='treasury_al_alert_t_idx'),
        ),
        migrations.AddIndex(
            model_name='alert',
            index=models.Index(fields=['resolved_at'], name='treasury_al_resolve_idx'),
        ),
        migrations.AddIndex(
            model_name='fundforecast',
            index=models.Index(fields=['fund', 'forecast_date'], name='treasury_fu_fund_id_idx'),
        ),
        migrations.AddIndex(
            model_name='fundforecast',
            index=models.Index(fields=['needs_replenishment', 'forecast_date'], name='treasury_fu_needs_r_idx'),
        ),
    ]
