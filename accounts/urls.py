from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import views_invitation
from . import views_bulk_import
from . import views_admin
from . import views_apps

app_name = 'accounts'

urlpatterns = [
    # --------------------------
    # Authentication
    # --------------------------
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html'
    ), name='login'),

    # Logout using POST only (default safe)
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Optional: GET logout redirect with warning
    # path('logout-get/', views.logout_get_redirect, name='logout-get'),

    # --------------------------
    # Password management
    # --------------------------
    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change_form.html'
    ), name='password_change'),

    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html'
    ), name='password_change_done'),

    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html'
    ), name='password_reset'),

    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html'
    ), name='password_reset_confirm'),

    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),

    # --------------------------
    # Dashboard & Role Redirect
    # --------------------------
    path('', views.dashboard, name='accounts-dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('role-redirect/', views.role_based_redirect, name='role_redirect'),
    
    # --------------------------
    # User Invitations & Signup
    # --------------------------
    path('invite/', views_invitation.send_invitation, name='invite_user'),
    path('invitations/', views_invitation.manage_invitations, name='manage_invitations'),
    path('invitations/<int:invitation_id>/revoke/', views_invitation.revoke_invitation, name='revoke_invitation'),
    path('invitations/<int:invitation_id>/resend/', views_invitation.resend_invitation, name='resend_invitation'),
    path('signup/<uuid:token>/', views_invitation.signup, name='signup'),
    
    # Bulk import
    path('bulk-import/', views_bulk_import.bulk_import, name='bulk_import'),
    path('download-template/', views_bulk_import.download_template, name='download_template'),
    
    # --------------------------
    # Device Management
    # --------------------------
    path('my-devices/', views_invitation.my_devices, name='my_devices'),
    path('devices/<int:device_id>/deactivate/', views_invitation.deactivate_device, name='deactivate_device'),
    path('devices/<int:device_id>/set-primary/', views_invitation.set_primary_device, name='set_primary_device'),
    path('users/<int:user_id>/devices/', views_invitation.manage_user_devices, name='manage_user_devices'),
    
    # Admin device management actions
    path('admin/devices/<int:device_id>/toggle/', views_invitation.admin_toggle_device, name='admin_toggle_device'),
    path('admin/devices/<int:device_id>/delete/', views_invitation.admin_delete_device, name='admin_delete_device'),
    path('admin/devices/<int:device_id>/set-primary/', views_invitation.admin_set_primary_device, name='admin_set_primary_device'),
    
    # --------------------------
    # Admin Dashboard & User Management
    # --------------------------
    path('manage-users/', views_admin.manage_users, name='manage_users'),
    path('users/<int:user_id>/edit-permissions/', views_admin.edit_user_permissions, name='edit_user_permissions'),
    path('users/<int:user_id>/toggle-status/', views_admin.toggle_user_status, name='toggle_user_status'),
    path('bulk-assign-app/', views_admin.bulk_assign_app, name='bulk_assign_app'),
    
    # Permission Groups Management
    path('groups/', views_admin.manage_groups, name='manage_groups'),
    path('groups/create/', views_admin.create_group, name='create_group'),
    path('groups/<int:group_id>/edit/', views_admin.edit_group, name='edit_group'),
    path('groups/<int:group_id>/delete/', views_admin.delete_group, name='delete_group'),
    
    # --------------------------
    # App Management
    # --------------------------
    path('apps/', views_apps.manage_apps, name='manage_apps'),
    path('apps/create/', views_apps.create_app, name='create_app'),
    path('apps/<int:app_id>/edit/', views_apps.edit_app, name='edit_app'),
    path('apps/<int:app_id>/toggle/', views_apps.toggle_app_status, name='toggle_app_status'),
    path('apps/<int:app_id>/users/', views_apps.app_users, name='app_users'),
    path('users/<int:user_id>/assign-apps/', views_apps.assign_apps_to_user, name='assign_apps_to_user'),
    path('bulk-assign-apps/', views_apps.bulk_assign_apps, name='bulk_assign_apps'),
    
    # Device blocking and registration
    path('device-blocked/', views_invitation.device_blocked, name='device_blocked'),
    path('request-device/', views_invitation.request_device_registration, name='request_device'),
]
