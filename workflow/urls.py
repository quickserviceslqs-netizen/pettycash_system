from django.urls import path
from workflow.views import workflow_dashboard

app_name = 'workflow'

urlpatterns = [
    path('', workflow_dashboard, name='dashboard'),
]
