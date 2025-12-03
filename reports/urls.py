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
    path('transactions/export/csv', views.transaction_report_export_csv, name='transaction-report-export-csv'),
    path('transactions/export/xlsx', views.transaction_report_export_xlsx, name='transaction-report-export-xlsx'),
    path('treasury/', views.treasury_report, name='treasury-report'),
    path('approvals/', views.approval_report, name='approval-report'),
    path('user-activity/', views.user_activity_report, name='user-activity-report'),
    # Exceptions
    path('exceptions/stuck-approvals/', views.stuck_approvals_report, name='stuck-approvals-report'),
]
