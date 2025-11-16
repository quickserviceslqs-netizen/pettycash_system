from django.contrib import admin
from .models import Payment, PaymentExecution, TreasuryFund, LedgerEntry, VarianceAdjustment, ReplenishmentRequest


@admin.register(TreasuryFund)
class TreasuryFundAdmin(admin.ModelAdmin):
    list_display = ('company', 'region', 'branch', 'current_balance', 'reorder_level', 'last_replenished')
    list_filter = ('company', 'created_at')
    search_fields = ('company__name', 'region__name', 'branch__name')
    readonly_fields = ('fund_id', 'created_at', 'updated_at')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'requisition', 'amount', 'method', 'status', 'executor', 'created_at')
    list_filter = ('status', 'method', 'otp_verified', 'created_at')
    search_fields = ('payment_id', 'requisition__transaction_id', 'destination')
    readonly_fields = ('payment_id', 'created_at', 'updated_at', 'execution_timestamp')


@admin.register(PaymentExecution)
class PaymentExecutionAdmin(admin.ModelAdmin):
    list_display = ('execution_id', 'payment', 'executor', 'gateway_status', 'execution_timestamp')
    list_filter = ('gateway_status', 'execution_timestamp')
    search_fields = ('execution_id', 'gateway_reference', 'executor__username')
    readonly_fields = ('execution_id', 'execution_timestamp')


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ('entry_id', 'treasury_fund', 'entry_type', 'amount', 'reconciled', 'created_at')
    list_filter = ('entry_type', 'reconciled', 'created_at')
    search_fields = ('description', 'treasury_fund__company__name')
    readonly_fields = ('entry_id', 'created_at')


@admin.register(VarianceAdjustment)
class VarianceAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('adjustment_id', 'treasury_fund', 'variance_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('reason', 'treasury_fund__company__name')
    readonly_fields = ('adjustment_id', 'variance_amount', 'created_at')


@admin.register(ReplenishmentRequest)
class ReplenishmentRequestAdmin(admin.ModelAdmin):
    list_display = ('request_id', 'treasury_fund', 'requested_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('reason', 'treasury_fund__company__name')
    readonly_fields = ('request_id', 'created_at')
