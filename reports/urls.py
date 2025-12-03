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
    path('approvals/export/logs.csv', views.approval_logs_export_csv, name='approval-logs-export-csv'),
    path('approvals/export/logs.xlsx', views.approval_logs_export_xlsx, name='approval-logs-export-xlsx'),
    path('approvals/export/approvers.csv', views.approver_perf_export_csv, name='approver-perf-export-csv'),
    path('approvals/export/approvers.xlsx', views.approver_perf_export_xlsx, name='approver-perf-export-xlsx'),
    path('user-activity/', views.user_activity_report, name='user-activity-report'),
    # Exceptions
    path('exceptions/stuck-approvals/', views.stuck_approvals_report, name='stuck-approvals-report'),
    path('exceptions/threshold-overrides/', views.threshold_overrides_report, name='threshold-overrides-report'),
    path('exceptions/threshold-overrides/export.csv', views.threshold_overrides_export_csv, name='threshold-overrides-export-csv'),
]
