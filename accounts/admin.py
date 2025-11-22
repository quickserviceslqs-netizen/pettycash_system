from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, Permission
from django.utils.html import format_html
from .models import User, App


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    """Admin for managing available applications."""
    list_display = ('display_name', 'name', 'url', 'is_active', 'user_count')
    list_filter = ('is_active',)
    search_fields = ('name', 'display_name', 'description')
    ordering = ('display_name',)
    
    fieldsets = (
        (None, {
            'fields': ('name', 'display_name', 'url', 'description', 'is_active')
        }),
    )
    
    def user_count(self, obj):
        """Show how many users have this app assigned."""
        count = obj.users.count()
        return format_html(
            '<span style="font-weight: bold;">{}</span> users',
            count
        )
    user_count.short_description = 'Assigned Users'


class UserRoleFilter(admin.SimpleListFilter):
    """Custom filter for user roles with counts."""
    title = 'role'
    parameter_name = 'role'

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
        'username', 'display_name_column', 'email', 'role_badge', 
        'company', 'branch', 'department',
        'is_centralized_approver', 'accessible_apps', 
        'is_staff', 'is_active'
    )
    list_filter = (
        UserRoleFilter, 'company', 'region', 'branch', 'department', 
        'is_centralized_approver',
        'is_staff', 'is_superuser', 'is_active'
    )
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number')
    ordering = ('username',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'email', 'phone_number')
        }),
        ('Role & Organizational Hierarchy', {
            'fields': (
                'role', 'company', 'region', 'branch', 
                'department', 'cost_center', 'position_title'
            ),
            'description': 'User role determines default app access and approval permissions.'
        }),
        ('App Access', {
            'fields': ('assigned_apps',),
            'description': 'Assign specific applications this user can access. Use Django permissions below to control what they can do within each app (add/view/change/delete).'
        }),
        ('Special Permissions', {
            'fields': ('is_centralized_approver',),
            'description': 'Centralized approvers can approve requisitions across the entire company.'
        }),
        ('System Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser', 
                'groups', 'user_permissions'
            ),
            'classes': ('collapse',),
            'description': 'Django Admin access and granular permissions. Use user_permissions to control add/view/change/delete actions within assigned apps.'
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email', 'role', 'company', 'assigned_apps'),
        }),
    )
    
    filter_horizontal = ('assigned_apps', 'groups', 'user_permissions')  # Better UI for many-to-many
    
    readonly_fields = ('last_login', 'date_joined')
    
    # Custom display methods
    def display_name_column(self, obj):
        """Show full name with username fallback."""
        name = obj.get_display_name()
        if name != obj.username:
            return format_html('<strong>{}</strong><br><small class="text-muted">{}</small>', name, obj.username)
        return name
    display_name_column.short_description = 'Display Name'
    
    def role_badge(self, obj):
        """Show role with color-coded badge."""
        colors = {
            'admin': '#dc3545',
            'ceo': '#6f42c1',
            'cfo': '#0d6efd',
            'group_finance_manager': '#0dcaf0',
            'regional_manager': '#20c997',
            'branch_manager': '#198754',
            'department_head': '#ffc107',
            'treasury': '#fd7e14',
            'fp&a': '#0dcaf0',
            'staff': '#6c757d',
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 8px; border-radius:3px; font-size:11px;">{}</span>',
            color, obj.get_role_display()
        )
    role_badge.short_description = 'Role'
    
    def accessible_apps(self, obj):
        """Show which apps this user has assigned."""
        apps = obj.assigned_apps.filter(is_active=True)
        if not apps.exists():
            # Fallback to role-based access
            from accounts.views import ROLE_ACCESS
            role_apps = ROLE_ACCESS.get(obj.role_key, [])
            if not role_apps:
                return format_html('<span style="color:#dc3545;">No apps</span>')
            app_list = role_apps
            note = '<br><small class="text-muted">(from role)</small>'
        else:
            app_list = [app.name for app in apps]
            note = ''
        
        app_badges = []
        for app in app_list:
            app_badges.append(f'<span style="background:#e9ecef; padding:2px 6px; border-radius:3px; margin:2px; display:inline-block; font-size:11px;">{app}</span>')
        
        return format_html(' '.join(app_badges) + note)
    accessible_apps.short_description = 'Accessible Apps'
    
    # Enhanced actions
    actions = ['activate_users', 'deactivate_users', 'make_centralized_approver', 'remove_centralized_approver']
    
    def activate_users(self, request, queryset):
        """Activate selected users."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} user(s) activated successfully.')
    activate_users.short_description = 'Activate selected users'
    
    def deactivate_users(self, request, queryset):
        """Deactivate selected users."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} user(s) deactivated successfully.')
    deactivate_users.short_description = 'Deactivate selected users'
    
    def make_centralized_approver(self, request, queryset):
        """Make selected users centralized approvers."""
        updated = queryset.update(is_centralized_approver=True)
        self.message_user(request, f'{updated} user(s) marked as centralized approvers.')
    make_centralized_approver.short_description = 'Mark as centralized approver'
    
    def remove_centralized_approver(self, request, queryset):
        """Remove centralized approver status."""
        updated = queryset.update(is_centralized_approver=False)
        self.message_user(request, f'{updated} user(s) removed from centralized approvers.')
    remove_centralized_approver.short_description = 'Remove centralized approver status'


# Register Django's built-in Permission model for easier management
@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """Enhanced permission management."""
    list_display = ('name', 'content_type', 'codename')
    list_filter = ('content_type',)
    search_fields = ('name', 'codename')
    ordering = ('content_type', 'codename')


# Customize Group admin for role-based access
class GroupAdmin(admin.ModelAdmin):
    """Enhanced group management for role-based permissions."""
    list_display = ('name', 'user_count', 'permission_count')
    search_fields = ('name',)
    filter_horizontal = ('permissions',)
    
    def user_count(self, obj):
        """Show number of users in this group."""
        count = obj.user_set.count()
        return format_html('<strong>{}</strong>', count)
    user_count.short_description = 'Users'
    
    def permission_count(self, obj):
        """Show number of permissions in this group."""
        count = obj.permissions.count()
        return format_html('<strong>{}</strong>', count)
    permission_count.short_description = 'Permissions'


# Unregister the default Group admin and register our custom one
admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)
