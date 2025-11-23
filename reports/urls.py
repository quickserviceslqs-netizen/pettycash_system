from django.urls import path
from . import views

app_name = 'reports'

# ---------------------------------------------------------------------
# URL patterns
# ---------------------------------------------------------------------
urlpatterns = [
    # Main dashboard
    path('', views.reports_dashboard, name='dashboard'),
    path('dashboard/', views.reports_dashboard, name='reports-dashboard'),
    
    # Detailed reports
    path('transactions/', views.transaction_report, name='transaction-report'),
    path('treasury/', views.treasury_report, name='treasury-report'),
    path('approvals/', views.approval_report, name='approval-report'),
    path('user-activity/', views.user_activity_report, name='user-activity-report'),
]
