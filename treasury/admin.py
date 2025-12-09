from django.contrib import admin

from .models import (
    Alert,
    DashboardMetric,
    FundForecast,
    LedgerEntry,
    Payment,
    PaymentExecution,
    PaymentTracking,
    ReplenishmentRequest,
    TreasuryDashboard,
    TreasuryFund,
    VarianceAdjustment,
)


@admin.register(TreasuryFund)
class TreasuryFundAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "region",
        "branch",
        "current_balance",
        "reorder_level",
        "last_replenished",
    )
    list_filter = ("company", "created_at")
    search_fields = ("company__name", "region__name", "branch__name")
    readonly_fields = ("fund_id", "created_at", "updated_at")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "payment_id",
        "requisition",
        "amount",
        "method",
        "status",
        "executor",
        "created_at",
    )
    list_filter = ("status", "method", "otp_verified", "created_at")
    search_fields = ("payment_id", "requisition__transaction_id", "destination")
    readonly_fields = ("payment_id", "created_at", "updated_at", "execution_timestamp")


@admin.register(PaymentExecution)
class PaymentExecutionAdmin(admin.ModelAdmin):
    list_display = (
        "execution_id",
        "payment",
        "executor",
        "gateway_status",
        "execution_timestamp",
    )
    list_filter = ("gateway_status", "execution_timestamp")
    search_fields = ("execution_id", "gateway_reference", "executor__username")
    readonly_fields = ("execution_id", "execution_timestamp")


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = (
        "entry_id",
        "treasury_fund",
        "entry_type",
        "amount",
        "reconciled",
        "created_at",
    )
    list_filter = ("entry_type", "reconciled", "created_at")
    search_fields = ("description", "treasury_fund__company__name")
    readonly_fields = ("entry_id", "created_at")


@admin.register(VarianceAdjustment)
class VarianceAdjustmentAdmin(admin.ModelAdmin):
    list_display = (
        "adjustment_id",
        "treasury_fund",
        "variance_amount",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("reason", "treasury_fund__company__name")
    readonly_fields = ("adjustment_id", "variance_amount", "created_at")


@admin.register(ReplenishmentRequest)
class ReplenishmentRequestAdmin(admin.ModelAdmin):
    list_display = (
        "request_id",
        "treasury_fund",
        "requested_amount",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("reason", "treasury_fund__company__name")
    readonly_fields = ("request_id", "created_at")


# ===== PHASE 6: DASHBOARD & REPORTING ADMIN CLASSES =====


@admin.register(TreasuryDashboard)
class TreasuryDashboardAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "total_balance",
        "active_alerts",
        "critical_alerts",
        "calculated_at",
    )
    list_filter = ("company", "calculated_at")
    search_fields = ("company__name", "region__name", "branch__name")
    readonly_fields = (
        "dashboard_id",
        "total_funds",
        "total_balance",
        "total_utilization_pct",
        "funds_below_reorder",
        "funds_critical",
        "payments_today",
        "payments_this_week",
        "payments_this_month",
        "total_amount_today",
        "total_amount_this_week",
        "total_amount_this_month",
        "active_alerts",
        "critical_alerts",
        "pending_replenishments",
        "pending_replenishment_amount",
        "pending_variances",
        "pending_variance_amount",
        "last_updated",
        "calculated_at",
    )


@admin.register(DashboardMetric)
class DashboardMetricAdmin(admin.ModelAdmin):
    list_display = ("dashboard", "metric_type", "metric_date", "value")
    list_filter = ("metric_type", "metric_date")
    search_fields = ("dashboard__company__name",)
    readonly_fields = ("metric_id", "created_at")


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = (
        "alert_id",
        "severity",
        "alert_type",
        "title",
        "is_unresolved",
        "created_at",
    )
    list_filter = ("severity", "alert_type", "resolved_at", "created_at")
    search_fields = ("title", "message", "related_fund__company__name")
    readonly_fields = ("alert_id", "created_at", "acknowledged_at", "resolved_at")

    fieldsets = (
        (
            "Alert Info",
            {"fields": ("alert_id", "alert_type", "severity", "title", "message")},
        ),
        (
            "Related Records",
            {"fields": ("related_payment", "related_fund", "related_variance")},
        ),
        (
            "Acknowledgment",
            {
                "fields": ("acknowledged_at", "acknowledged_by"),
                "classes": ("collapse",),
            },
        ),
        (
            "Resolution",
            {
                "fields": ("resolved_at", "resolved_by", "resolution_notes"),
                "classes": ("collapse",),
            },
        ),
        (
            "Email Tracking",
            {"fields": ("email_sent", "email_sent_at"), "classes": ("collapse",)},
        ),
        ("Timestamps", {"fields": ("created_at",), "classes": ("collapse",)}),
    )


@admin.register(PaymentTracking)
class PaymentTrackingAdmin(admin.ModelAdmin):
    list_display = (
        "tracking_id",
        "payment",
        "current_status",
        "created_at",
        "total_execution_time",
    )
    list_filter = ("current_status", "created_at")
    search_fields = ("payment__payment_id", "tracking_id")
    readonly_fields = (
        "tracking_id",
        "created_at",
        "otp_sent_at",
        "otp_verified_at",
        "execution_started_at",
        "execution_completed_at",
        "reconciliation_started_at",
        "reconciliation_completed_at",
        "total_execution_time",
        "otp_verification_time",
    )


@admin.register(FundForecast)
class FundForecastAdmin(admin.ModelAdmin):
    list_display = (
        "fund",
        "forecast_date",
        "predicted_balance",
        "needs_replenishment",
        "confidence_level",
    )
    list_filter = ("needs_replenishment", "forecast_date", "forecast_horizon_days")
    search_fields = ("fund__company__name", "fund__region__name", "fund__branch__name")
    readonly_fields = ("forecast_id", "calculated_at")
