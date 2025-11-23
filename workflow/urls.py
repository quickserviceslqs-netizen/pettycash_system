from django.urls import path
from workflow.views import workflow_dashboard, threshold_edit

app_name = 'workflow'

urlpatterns = [
    path('', workflow_dashboard, name='dashboard'),
    path('threshold/<int:threshold_id>/edit/', threshold_edit, name='threshold_edit'),
]
