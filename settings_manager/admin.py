from django.contrib import admin
from settings_manager.models import SystemSetting, ActivityLog


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "key",
        "category",
        "setting_type",
        "is_active",
        "last_modified_at",
    )
    list_filter = ("category", "setting_type", "is_active", "editable_by_admin")
    search_fields = ("key", "display_name", "description")
    readonly_fields = ("last_modified_by", "last_modified_at", "created_at")

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("key", "display_name", "description", "category")},
        ),
        ("Value Configuration", {"fields": ("setting_type", "value", "default_value")}),
        (
            "Permissions & Behavior",
            {
                "fields": (
                    "is_active",
                    "editable_by_admin",
                    "is_sensitive",
                    "requires_restart",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": ("last_modified_by", "last_modified_at", "created_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        "timestamp",
        "user",
        "action",
        "content_type",
        "object_repr",
        "success",
    )
    list_filter = ("action", "success", "timestamp")
    search_fields = ("user__username", "description", "object_repr")
    readonly_fields = (
        "user",
        "action",
        "timestamp",
        "ip_address",
        "user_agent",
        "content_type",
        "object_id",
        "description",
        "changes",
        "success",
        "error_message",
    )

    def has_add_permission(self, request):
        return False  # Logs are auto-generated only

    def has_change_permission(self, request, obj=None):
        return False  # Logs are immutable
