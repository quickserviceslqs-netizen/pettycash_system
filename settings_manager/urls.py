from django.urls import path
from settings_manager import views

app_name = 'settings_manager'

urlpatterns = [
    # Settings Management
    path('', views.settings_dashboard, name='dashboard'),
    path('edit/<int:setting_id>/', views.edit_setting, name='edit_setting'),
    path('activity-logs/', views.activity_logs, name='activity_logs'),
    path('system-info/', views.system_info, name='system_info'),
    
    # Data Operations
    path('data/', views.data_operations_dashboard, name='data_operations'),
    
    # User Management
    path('data/users/', views.manage_users, name='manage_users'),
    path('data/users/create/', views.create_user, name='create_user'),
    path('data/users/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('data/users/toggle/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    path('data/users/export/', views.export_users_csv, name='export_users'),
    
    # Department Management
    path('data/departments/', views.manage_departments, name='manage_departments'),
    path('data/departments/create/', views.create_department, name='create_department'),
    
    # Region Management
    path('data/regions/', views.manage_regions, name='manage_regions'),
]
