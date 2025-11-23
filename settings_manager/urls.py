from django.urls import path
from settings_manager import views

app_name = 'settings_manager'

urlpatterns = [
    path('', views.settings_dashboard, name='dashboard'),
    path('edit/<int:setting_id>/', views.edit_setting, name='edit_setting'),
    path('activity-logs/', views.activity_logs, name='activity_logs'),
    path('system-info/', views.system_info, name='system_info'),
]
