from django.urls import path
from settings_manager import views

urlpatterns = [
    path('', views.settings_dashboard, name='settings-dashboard'),
    path('edit/<int:setting_id>/', views.edit_setting, name='edit-setting'),
    path('activity-logs/', views.activity_logs, name='activity-logs'),
    path('system-info/', views.system_info, name='system-info'),
]
