from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username', 'email', 'role', 'company', 'region', 'branch', 
        'department', 'cost_center', 'position_title', 
        'is_centralized_approver',  # NEW
        'is_staff', 'is_superuser'
    )
    list_filter = (
        'role', 'company', 'region', 'branch', 'department', 
        'is_centralized_approver',  # NEW
        'is_staff', 'is_superuser'
    )
    search_fields = ('username', 'email', 'phone_number')
    ordering = ('username',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        ('Organizational info', {'fields': (
            'role', 'company', 'region', 'branch', 'department', 'cost_center', 
            'position_title', 'is_centralized_approver'  # NEW
        )}),
        ('Permissions', {'fields': (
            'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'
        )}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
