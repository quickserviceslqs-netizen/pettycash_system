"""
Locust Load Testing Scenarios for Petty Cash Management System
Phase 7: Performance and Load Testing

Usage:
    # Install locust
    pip install locust

    # Run against local development
    locust -f load_tests/locustfile.py --host=http://localhost:8000

    # Run against staging
    locust -f load_tests/locustfile.py --host=https://staging.example.com

    # Web UI: http://localhost:8089
    # Command line: locust -f locustfile.py --host=http://localhost:8000 --users 100 --spawn-rate 10
"""

from locust import HttpUser, TaskSet, task, between, SequentialTaskSet
from random import randint, choice
import json


class DashboardTasks(TaskSet):
    """Treasury Dashboard Load Testing"""
    
    @task(10)
    def view_dashboard_metrics(self):
        """Load dashboard with real-time metrics"""
        with self.client.get(
            "/treasury/api/dashboard/metrics/",
            catch_response=True,
            name="Dashboard: Metrics"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                response.failure("Authentication required")
    
    @task(5)
    def view_pending_payments(self):
        """Load pending payments list"""
        with self.client.get(
            "/treasury/api/dashboard/pending-payments/",
            catch_response=True,
            name="Dashboard: Pending Payments"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if len(data) > 1000:
                    response.failure("Too many pending items - performance issue")
                else:
                    response.success()
    
    @task(3)
    def view_recent_payments(self):
        """Load recent payments history"""
        self.client.get(
            "/treasury/api/dashboard/recent-payments/?limit=50",
            name="Dashboard: Recent Payments"
        )
    
    @task(8)
    def view_alerts(self):
        """Load active alerts"""
        self.client.get(
            "/treasury/api/alerts/?status=active",
            name="Dashboard: Active Alerts"
        )


class RequisitionWorkflow(SequentialTaskSet):
    """Complete requisition workflow sequence"""
    
    def on_start(self):
        """Setup test data"""
        self.transaction_id = f"PERF-{randint(10000, 99999)}"
        self.requisition_id = None
    
    @task
    def create_requisition(self):
        """Step 1: Create requisition"""
        payload = {
            'transaction_id': self.transaction_id,
            'requested_by': randint(1, 5),
            'origin_type': 'branch',
            'company': 1,
            'branch': randint(1, 3),
            'amount': str(randint(100, 5000)),
            'purpose': f'Performance test requisition {self.transaction_id}',
            'is_urgent': choice([True, False])
        }
        
        with self.client.post(
            "/api/requisitions/",
            json=payload,
            catch_response=True,
            name="Workflow: Create Requisition"
        ) as response:
            if response.status_code == 201:
                self.requisition_id = response.json().get('transaction_id')
                response.success()
            else:
                response.failure(f"Failed to create: {response.status_code}")
    
    @task
    def apply_threshold(self):
        """Step 2: Apply approval threshold"""
        if self.requisition_id:
            self.client.post(
                f"/api/requisitions/{self.requisition_id}/apply-threshold/",
                name="Workflow: Apply Threshold"
            )
    
    @task
    def resolve_workflow(self):
        """Step 3: Resolve approval workflow"""
        if self.requisition_id:
            self.client.post(
                f"/api/requisitions/{self.requisition_id}/resolve-workflow/",
                name="Workflow: Resolve Workflow"
            )
    
    @task
    def check_status(self):
        """Step 4: Check requisition status"""
        if self.requisition_id:
            self.client.get(
                f"/api/requisitions/{self.requisition_id}/",
                name="Workflow: Check Status"
            )


class PaymentExecutionTasks(TaskSet):
    """Payment execution and tracking"""
    
    @task(3)
    def list_pending_payments(self):
        """Get list of payments ready for execution"""
        self.client.get(
            "/treasury/api/payments/?status=pending",
            name="Payment: List Pending"
        )
    
    @task(1)
    def request_otp(self):
        """Request OTP for payment execution"""
        payment_id = f"pay-{randint(1, 100)}"
        self.client.post(
            f"/treasury/api/payments/{payment_id}/request-otp/",
            name="Payment: Request OTP",
            catch_response=True
        )
    
    @task(2)
    def check_payment_status(self):
        """Check payment execution status"""
        payment_id = f"pay-{randint(1, 100)}"
        self.client.get(
            f"/treasury/api/payments/{payment_id}/status/",
            name="Payment: Check Status"
        )


class AlertManagementTasks(TaskSet):
    """Alert monitoring and management"""
    
    @task(5)
    def list_alerts_by_severity(self):
        """List alerts filtered by severity"""
        severity = choice(['Critical', 'High', 'Medium', 'Low'])
        self.client.get(
            f"/treasury/api/alerts/?severity={severity}",
            name=f"Alerts: {severity}"
        )
    
    @task(2)
    def acknowledge_alert(self):
        """Acknowledge an alert"""
        alert_id = randint(1, 50)
        self.client.post(
            f"/treasury/api/alerts/{alert_id}/acknowledge/",
            json={'acknowledged_by': randint(1, 5)},
            name="Alerts: Acknowledge"
        )
    
    @task(1)
    def resolve_alert(self):
        """Resolve an alert"""
        alert_id = randint(1, 50)
        self.client.post(
            f"/treasury/api/alerts/{alert_id}/resolve/",
            json={
                'resolved_by': randint(1, 5),
                'resolution_notes': 'Performance test resolution'
            },
            name="Alerts: Resolve"
        )


class ReportingTasks(TaskSet):
    """Reporting and analytics"""
    
    @task(3)
    def payment_summary_report(self):
        """Generate payment summary report"""
        self.client.get(
            "/reports/api/payment-summary/?days=30",
            name="Reports: Payment Summary"
        )
    
    @task(2)
    def fund_health_report(self):
        """Generate fund health report"""
        self.client.get(
            "/reports/api/fund-health/",
            name="Reports: Fund Health"
        )
    
    @task(2)
    def variance_analysis(self):
        """Generate variance analysis report"""
        self.client.get(
            "/reports/api/variance-analysis/?days=30",
            name="Reports: Variance Analysis"
        )


class TreasuryUser(HttpUser):
    """Treasury Department User - High Activity"""
    wait_time = between(1, 3)
    weight = 3
    
    tasks = {
        DashboardTasks: 5,
        PaymentExecutionTasks: 3,
        AlertManagementTasks: 2
    }


class FinanceUser(HttpUser):
    """Finance/FP&A User - Report Focused"""
    wait_time = between(2, 5)
    weight = 2
    
    tasks = {ReportingTasks: 1}


class BranchUser(HttpUser):
    """Branch Staff - Requisition Focused"""
    wait_time = between(2, 4)
    weight = 5
    
    tasks = {RequisitionWorkflow: 1}


class GeneralUser(HttpUser):
    """General Mixed User"""
    wait_time = between(1, 5)
    weight = 3
    
    tasks = {
        DashboardTasks: 3,
        AlertManagementTasks: 1,
        ReportingTasks: 1
    }

