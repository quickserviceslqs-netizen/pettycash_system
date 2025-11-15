from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

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
]
