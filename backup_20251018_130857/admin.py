from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('requisition', 'paid_amount', 'paid_at', 'processed_by')
    list_filter = ('paid_at', 'processed_by')
    search_fields = ('requisition__transaction_id', 'processed_by__username')
    readonly_fields = ('paid_at',)
