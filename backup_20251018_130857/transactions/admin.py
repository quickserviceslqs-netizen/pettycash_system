from django.contrib import admin
from .models import Requisition, ApprovalTrail

@admin.register(Requisition)
class RequisitionAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_id', 'requested_by', 'origin_type', 'company', 'region', 
        'branch', 'department', 'amount', 'status', 'created_at', 'updated_at'
    )
    list_filter = ('status', 'origin_type', 'company', 'region', 'branch', 'department')
    search_fields = ('transaction_id', 'requested_by__username', 'purpose')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

@admin.register(ApprovalTrail)
class ApprovalTrailAdmin(admin.ModelAdmin):
    list_display = ('requisition', 'user', 'role', 'action', 'timestamp', 'auto_escalated', 'override')
    list_filter = ('action', 'role', 'auto_escalated', 'override')
    search_fields = ('requisition__transaction_id', 'user__username', 'comment')
    readonly_fields = ('timestamp',)
