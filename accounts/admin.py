from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, Permission
from django.utils.html import format_html
from .models import User, App
from .models_device import UserInvitation, WhitelistedDevice, DeviceAccessAttempt


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    """Admin for managing available applications."""

    list_display = ("display_name", "name", "url", "is_active", "user_count")
    list_filter = ("is_active",)
    search_fields = ("name", "display_name", "description")
    ordering = ("display_name",)

    fieldsets = (
        (None, {"fields": ("name", "display_name", "url", "description", "is_active")}),
    )

    def user_count(self, obj):
        """Show how many users have this app assigned."""
        count = obj.users.count()
        return format_html('<span style="font-weight: bold;">{}</span> users', count)

    user_count.short_description = "Assigned Users"


class UserRoleFilter(admin.SimpleListFilter):
    """Custom filter for user roles with counts."""

    title = "role"
    parameter_name = "role"

    def lookups(self, request, model_admin):
        roles = User.ROLE_CHOICES
        return roles

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(role=self.value())
        return queryset


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced User admin with app assignment and permission management."""

    list_display = (
        "username",
        "display_name_column",
        "email",
        "role_badge",
        "company",
        "branch",
        "department",
        "is_centralized_approver",
        "accessible_apps",
        "is_staff",
        "is_active",
    )
    list_filter = (
        UserRoleFilter,
        "company",
        "region",
        "branch",
        "department",
        "is_centralized_approver",
        "is_staff",
        "is_superuser",
        "is_active",
    )
    search_fields = ("username", "email", "first_name", "last_name", "phone_number")
    ordering = ("username",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal Information",
            {"fields": ("first_name", "last_name", "email", "phone_number")},
        ),
        (
            "Role & Organizational Hierarchy",
            {
                "fields": (
                    "role",
                    "company",
                    "region",
                    "branch",
                    "department",
                    "cost_center",
                    "position_title",
                ),
                "description": "User role determines default app access and approval permissions.",
            },
        ),
        (
            "App Access",
            {
                "fields": ("assigned_apps",),
                "description": "Assign specific applications this user can access. Use Django permissions below to control what they can do within each app (add/view/change/delete).",
            },
        ),
        (
            "Special Permissions",
            {
                "fields": ("is_centralized_approver",),
                "description": "Centralized approvers can approve requisitions across the entire company.",
            },
        ),
        (
            "System Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "classes": ("collapse",),
                "description": "Django Admin access and granular permissions. Use user_permissions to control add/view/change/delete actions within assigned apps.",
            },
        ),
        (
            "Important Dates",
            {"fields": ("last_login", "date_joined"), "classes": ("collapse",)},
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                    "email",
                    "role",
                    "company",
                    "assigned_apps",
                ),
            },
        ),
    )

    filter_horizontal = (
        "assigned_apps",
        "groups",
        "user_permissions",
    )  # Better UI for many-to-many

    readonly_fields = ("last_login", "date_joined")

    # Custom display methods
    def display_name_column(self, obj):
        """Show full name with username fallback."""
        name = obj.get_display_name()
        if name != obj.username:
            return format_html(
                '<strong>{}</strong><br><small class="text-muted">{}</small>',
                name,
                obj.username,
            )
        return name

    display_name_column.short_description = "Display Name"

    def role_badge(self, obj):
        """Show role with color-coded badge."""
        colors = {
            "admin": "#dc3545",
            "ceo": "#6f42c1",
            "cfo": "#0d6efd",
            "group_finance_manager": "#0dcaf0",
            "regional_manager": "#20c997",
            "branch_manager": "#198754",
            "department_head": "#ffc107",
            "treasury": "#fd7e14",
            "fp&a": "#0dcaf0",
            "staff": "#6c757d",
        }
        color = colors.get(obj.role, "#6c757d")
        return format_html(
            '<span style="background:{}; color:white; padding:3px 8px; border-radius:3px; font-size:11px;">{}</span>',
            color,
            obj.get_role_display(),
        )

    role_badge.short_description = "Role"

    def accessible_apps(self, obj):
        """Show which apps this user has assigned."""
        apps = obj.assigned_apps.filter(is_active=True)
        if not apps.exists():
            return format_html('<span style="color:#dc3545;">No apps assigned</span>')

        app_list = [app.name for app in apps]

        app_badges = []
        for app in app_list:
            app_badges.append(
                f'<span style="background:#e9ecef; padding:2px 6px; border-radius:3px; margin:2px; display:inline-block; font-size:11px;">{app}</span>'
            )

        return format_html(" ".join(app_badges))

    accessible_apps.short_description = "Accessible Apps"

    # Enhanced actions
    actions = [
        "activate_users",
        "deactivate_users",
        "make_centralized_approver",
        "remove_centralized_approver",
    ]

    def activate_users(self, request, queryset):
        """Activate selected users."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} user(s) activated successfully.")

    activate_users.short_description = "Activate selected users"

    def deactivate_users(self, request, queryset):
        """Deactivate selected users."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} user(s) deactivated successfully.")

    deactivate_users.short_description = "Deactivate selected users"

    def make_centralized_approver(self, request, queryset):
        """Make selected users centralized approvers."""
        updated = queryset.update(is_centralized_approver=True)
        self.message_user(
            request, f"{updated} user(s) marked as centralized approvers."
        )

    make_centralized_approver.short_description = "Mark as centralized approver"

    def remove_centralized_approver(self, request, queryset):
        """Remove centralized approver status."""
        updated = queryset.update(is_centralized_approver=False)
        self.message_user(
            request, f"{updated} user(s) removed from centralized approvers."
        )

    remove_centralized_approver.short_description = "Remove centralized approver status"


# Register Django's built-in Permission model for easier management
@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """Enhanced permission management."""

    list_display = ("name", "content_type", "codename")
    list_filter = ("content_type",)
    search_fields = ("name", "codename")
    ordering = ("content_type", "codename")


# Customize Group admin for role-based access
class GroupAdmin(admin.ModelAdmin):
    """Enhanced group management for role-based permissions."""

    list_display = ("name", "user_count", "permission_count")
    search_fields = ("name",)
    filter_horizontal = ("permissions",)

    def user_count(self, obj):
        """Show number of users in this group."""
        count = obj.user_set.count()
        return format_html("<strong>{}</strong>", count)

    user_count.short_description = "Users"

    def permission_count(self, obj):
        """Show number of permissions in this group."""
        count = obj.permissions.count()
        return format_html("<strong>{}</strong>", count)

    permission_count.short_description = "Permissions"


# Unregister the default Group admin and register our custom one
admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)


# ===================================================================
# Device Management & Invitation Admin
# ===================================================================


@admin.register(UserInvitation)
class UserInvitationAdmin(admin.ModelAdmin):
    """Admin for managing user invitations."""

    list_display = (
        "email",
        "first_name",
        "last_name",
        "role",
        "status_badge",
        "invited_by",
        "created_at",
        "expires_at",
    )
    list_filter = ("status", "role", "created_at")
    search_fields = ("email", "first_name", "last_name")
    readonly_fields = ("token", "created_at", "accepted_at")
    ordering = ("-created_at",)

    fieldsets = (
        (
            "Recipient Information",
            {"fields": ("email", "first_name", "last_name", "role")},
        ),
        (
            "Organization",
            {"fields": ("company", "department", "branch", "assigned_apps")},
        ),
        (
            "Invitation Status",
            {"fields": ("status", "token", "created_at", "expires_at", "accepted_at")},
        ),
        ("Relationships", {"fields": ("invited_by", "user")}),
    )

    def status_badge(self, obj):
        """Show status with color badge."""
        colors = {
            "pending": "warning",
            "accepted": "success",
            "expired": "danger",
            "revoked": "secondary",
        }
        color = colors.get(obj.status, "secondary")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            {
                "warning": "#ffc107",
                "success": "#28a745",
                "danger": "#dc3545",
                "secondary": "#6c757d",
            }[color],
            obj.status.upper(),
        )

    status_badge.short_description = "Status"


@admin.register(WhitelistedDevice)
class WhitelistedDeviceAdmin(admin.ModelAdmin):
    """Admin for managing whitelisted devices."""

    list_display = (
        "user",
        "device_name",
        "ip_address",
        "location",
        "is_primary",
        "is_active",
        "registered_at",
        "last_used_at",
    )
    list_filter = ("is_active", "is_primary", "registration_method", "registered_at")
    search_fields = (
        "user__username",
        "user__email",
        "device_name",
        "ip_address",
        "location",
    )
    readonly_fields = ("registered_at", "last_used_at")
    ordering = ("-registered_at",)
    actions = ["activate_devices", "deactivate_devices", "delete_non_primary_devices"]

    fieldsets = (
        (
            "Device Information",
            {"fields": ("user", "device_name", "user_agent", "ip_address", "location")},
        ),
        ("Status", {"fields": ("is_active", "is_primary", "registration_method")}),
        ("Timestamps", {"fields": ("registered_at", "last_used_at")}),
        ("Notes", {"fields": ("notes",), "classes": ("collapse",)}),
    )

    def activate_devices(self, request, queryset):
        """Bulk activate selected devices"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} device(s) activated successfully.")

    activate_devices.short_description = "✓ Activate selected devices"

    def deactivate_devices(self, request, queryset):
        """Bulk deactivate selected non-primary devices"""
        # Don't deactivate primary devices
        non_primary = queryset.filter(is_primary=False)
        updated = non_primary.update(is_active=False)
        self.message_user(request, f"{updated} device(s) deactivated successfully.")
        if queryset.filter(is_primary=True).exists():
            self.message_user(
                request,
                "Primary devices were skipped (cannot deactivate).",
                level="warning",
            )

    deactivate_devices.short_description = (
        "⏸ Deactivate selected devices (skip primary)"
    )

    def delete_non_primary_devices(self, request, queryset):
        """Bulk delete selected non-primary devices"""
        primary_count = queryset.filter(is_primary=True).count()
        non_primary = queryset.filter(is_primary=False)
        count = non_primary.count()
        non_primary.delete()
        self.message_user(
            request, f"{count} non-primary device(s) deleted successfully."
        )
        if primary_count > 0:
            self.message_user(
                request,
                f"{primary_count} primary device(s) were skipped (cannot delete).",
                level="warning",
            )

    delete_non_primary_devices.short_description = (
        "🗑 Delete selected devices (skip primary)"
    )


@admin.register(DeviceAccessAttempt)
class DeviceAccessAttemptAdmin(admin.ModelAdmin):
    """Admin for viewing device access attempts (security audit)."""

    list_display = (
        "attempted_at",
        "user",
        "device_name",
        "ip_address",
        "location",
        "was_allowed_badge",
        "request_path",
    )
    list_filter = ("was_allowed", "attempted_at")
    search_fields = ("user__username", "ip_address", "device_name", "location")
    readonly_fields = (
        "user",
        "ip_address",
        "device_name",
        "user_agent",
        "location",
        "was_allowed",
        "reason",
        "attempted_at",
        "request_path",
    )
    ordering = ("-attempted_at",)

    def was_allowed_badge(self, obj):
        """Show access result with color badge."""
        if obj.was_allowed:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">✓ ALLOWED</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px;">✗ BLOCKED</span>'
            )

    was_allowed_badge.short_description = "Result"

    def has_add_permission(self, request):
        """Disable manual creation - these are system-generated logs."""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable editing - these are immutable audit logs."""
        return False
