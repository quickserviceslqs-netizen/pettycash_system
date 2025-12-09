from django.contrib import admin, messages
from .models import Requisition, ApprovalTrail
from workflow.services.resolver import find_approval_threshold, resolve_workflow


@admin.action(description="Apply Approval Threshold to selected requisitions")
def apply_threshold_action(modeladmin, request, queryset):
    for requisition in queryset:
        try:
            thr = requisition.apply_threshold()
            messages.success(
                request,
                f"Threshold '{thr.name}' applied to {requisition.transaction_id}",
            )
        except Exception as e:
            messages.error(
                request,
                f"Error applying threshold to {requisition.transaction_id}: {e}",
            )


@admin.action(description="Resolve workflow for selected requisitions")
def resolve_workflow_action(modeladmin, request, queryset):
    for requisition in queryset:
        if not requisition.applied_threshold:
            messages.warning(
                request,
                f"Cannot resolve workflow for {requisition.transaction_id}: Threshold not applied",
            )
            continue
        try:
            sequence = resolve_workflow(requisition)
            messages.success(
                request,
                f"Workflow resolved for {requisition.transaction_id}: {len(sequence)} approvers assigned",
            )
        except Exception as e:
            messages.error(
                request,
                f"Error resolving workflow for {requisition.transaction_id}: {e}",
            )


@admin.register(Requisition)
class RequisitionAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_id",
        "requested_by",
        "origin_type",
        "company",
        "region",
        "branch",
        "department",
        "amount",
        "status",
        "applied_threshold",
        "tier",
        "next_approver",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "origin_type", "company", "region", "branch", "department")
    search_fields = ("transaction_id", "requested_by__username", "purpose")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
    actions = [apply_threshold_action, resolve_workflow_action]


@admin.register(ApprovalTrail)
class ApprovalTrailAdmin(admin.ModelAdmin):
    list_display = (
        "requisition",
        "user",
        "role",
        "action",
        "timestamp",
        "auto_escalated",
        "override",
    )
    list_filter = ("action", "role", "auto_escalated", "override")
    search_fields = ("requisition__transaction_id", "user__username", "comment")
    readonly_fields = ("timestamp",)
