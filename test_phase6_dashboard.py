"""
Phase 6: Treasury Dashboard & Reporting - Comprehensive Test Suite

Tests:
1. Dashboard calculation and caching
2. Alert triggering and notification
3. Payment tracking timeline
4. Forecasting accuracy
5. Report generation
6. API endpoints
7. Export functionality
8. UI rendering
"""

import os
import django
from datetime import datetime, timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_settings')
django.setup()

from organization.models import Company, Region, Branch, Department
from treasury.models import (
    TreasuryFund, Payment, TreasuryDashboard, DashboardMetric, Alert, 
    PaymentTracking, FundForecast, LedgerEntry, VarianceAdjustment
)
from transactions.models import Requisition, ApprovalThreshold
from treasury.services.dashboard_service import DashboardService
from treasury.services.alert_service import AlertService
from treasury.services.report_service import ReportService

User = get_user_model()


class DashboardServiceTestCase(TestCase):
    """Test DashboardService calculation and caching."""
    
    def setUp(self):
        """Setup test data."""
        self.company = Company.objects.create(
            name='Test Company',
            code='TST'
        )
        
        self.region = Region.objects.create(
            name='North',
            company=self.company
        )
        
        self.branch = Branch.objects.create(
            name='Delhi',
            code='DEL',
            company=self.company,
            region=self.region
        )
        
        # Create funds
        self.fund1 = TreasuryFund.objects.create(
            company=self.company,
            region=self.region,
            branch=self.branch,
            current_balance=Decimal('2500000.00'),
            reorder_level=Decimal('1000000.00')
        )
        
        self.fund2 = TreasuryFund.objects.create(
            company=self.company,
            region=self.region,
            branch=None,
            current_balance=Decimal('850000.00'),
            reorder_level=Decimal('1000000.00')
        )
    
    def test_dashboard_calculation_basic(self):
        """Test basic dashboard metrics calculation."""
        dashboard = DashboardService.calculate_dashboard_metrics(self.company.id)
        
        self.assertIsNotNone(dashboard)
        self.assertEqual(dashboard.total_funds, 2)
        self.assertEqual(dashboard.total_balance, Decimal('3350000.00'))
        self.assertEqual(dashboard.funds_below_reorder, 1)
        self.assertEqual(dashboard.funds_critical, 0)
    
    def test_fund_status_cards(self):
        """Test fund status card generation."""
        cards = DashboardService.get_fund_status_cards(self.company.id)
        
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0]['status'], 'OK')
        self.assertEqual(cards[1]['status'], 'WARNING')
        self.assertAlmostEqual(cards[0]['utilization_pct'], 250.0, places=1)
    
    def test_fund_critical_status(self):
        """Test critical fund status calculation."""
        # Make fund critical
        self.fund2.current_balance = Decimal('700000.00')
        self.fund2.save()
        
        cards = DashboardService.get_fund_status_cards(self.company.id)
        
        critical_card = next(c for c in cards if c['fund_id'] == str(self.fund2.fund_id))
        self.assertEqual(critical_card['status'], 'CRITICAL')
    
    def test_dashboard_metrics_recording(self):
        """Test metric recording for trend analysis."""
        dashboard = DashboardService.calculate_dashboard_metrics(self.company.id)
        
        # Record metrics
        DashboardService.record_metric(dashboard, 'fund_balance', Decimal('3350000.00'))
        DashboardService.record_metric(dashboard, 'payment_volume', 5)
        
        metrics = DashboardMetric.objects.filter(dashboard=dashboard)
        self.assertEqual(metrics.count(), 2)
    
    def test_pending_payments_retrieval(self):
        """Test pending payments retrieval."""
        user = User.objects.create_user(username='treasury', password='pass123')
        
        # Create a payment
        requisition = Requisition.objects.create(
            transaction_id='REQ-001',
            origin_type='branch',
            requesting_user=user,
            amount=Decimal('50000.00'),
            purpose='Office Supplies'
        )
        
        payment = Payment.objects.create(
            requisition=requisition,
            treasury_fund=self.fund1,
            amount=requisition.amount,
            method='bank_transfer',
            destination='ACCOUNT-001',
            status='pending'
        )
        
        payments = DashboardService.get_pending_payments(self.company.id)
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments[0].payment_id, payment.payment_id)


class AlertServiceTestCase(TestCase):
    """Test AlertService alert creation and management."""
    
    def setUp(self):
        """Setup test data."""
        self.company = Company.objects.create(name="Test", code="TST")
        
        self.region = Region.objects.create(
            name='South',
            company=self.company
        )
        
        self.fund = TreasuryFund.objects.create(
            company=self.company,
            region=self.region,
            current_balance=Decimal('800000.00'),
            reorder_level=Decimal('1000000.00')
        )
        
        self.user = User.objects.create_user(username='treasurer', password='pass123')
    
    def test_fund_critical_alert_creation(self):
        """Test critical fund alert creation."""
        # Fund balance < 80% reorder
        self.fund.current_balance = Decimal('700000.00')
        self.fund.save()
        
        alert = AlertService.check_fund_critical(self.fund)
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert.severity, 'Critical')
        self.assertEqual(alert.alert_type, 'fund_critical')
        self.assertTrue(alert.related_fund.fund_id == self.fund.fund_id)
    
    def test_fund_low_alert_creation(self):
        """Test low fund alert creation."""
        # Fund balance between reorder and 80% of reorder
        self.fund.current_balance = Decimal('900000.00')
        self.fund.save()
        
        alert = AlertService.check_fund_low(self.fund)
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert.severity, 'High')
        self.assertEqual(alert.alert_type, 'fund_low')
    
    def test_alert_acknowledgment(self):
        """Test alert acknowledgment."""
        alert = Alert.objects.create(
            alert_type='fund_critical',
            severity='Critical',
            title='Test Alert',
            message='Test message',
            related_fund=self.fund
        )
        
        AlertService.acknowledge_alert(alert, self.user)
        alert.refresh_from_db()
        
        self.assertIsNotNone(alert.acknowledged_at)
        self.assertEqual(alert.acknowledged_by, self.user)
    
    def test_alert_resolution(self):
        """Test alert resolution."""
        alert = Alert.objects.create(
            alert_type='fund_critical',
            severity='Critical',
            title='Test Alert',
            message='Test message',
            related_fund=self.fund
        )
        
        AlertService.resolve_alert(alert, self.user, notes='Replenished')
        alert.refresh_from_db()
        
        self.assertIsNotNone(alert.resolved_at)
        self.assertEqual(alert.resolved_by, self.user)
        self.assertEqual(alert.resolution_notes, 'Replenished')
    
    def test_unresolved_alerts_query(self):
        """Test querying unresolved alerts."""
        # Create unresolved alert
        alert1 = Alert.objects.create(
            alert_type='fund_critical',
            severity='Critical',
            title='Alert 1',
            message='Message 1',
            related_fund=self.fund
        )
        
        # Create resolved alert
        alert2 = Alert.objects.create(
            alert_type='fund_low',
            severity='High',
            title='Alert 2',
            message='Message 2',
            related_fund=self.fund,
            resolved_at=timezone.now()
        )
        
        unresolved = AlertService.get_unresolved_alerts()
        self.assertTrue(any(a.alert_id == alert1.alert_id for a in unresolved))
        self.assertFalse(any(a.alert_id == alert2.alert_id for a in unresolved))
    
    def test_alert_summary(self):
        """Test alert summary by severity."""
        Alert.objects.create(
            alert_type='fund_critical',
            severity='Critical',
            title='Critical Alert',
            message='Message',
            related_fund=self.fund
        )
        
        Alert.objects.create(
            alert_type='fund_low',
            severity='High',
            title='High Alert',
            message='Message',
            related_fund=self.fund
        )
        
        summary = AlertService.get_alert_summary()
        self.assertEqual(summary['Critical'], 1)
        self.assertEqual(summary['High'], 1)
        self.assertEqual(summary['Total'], 2)


class ReportServiceTestCase(TestCase):
    """Test ReportService report generation."""
    
    def setUp(self):
        """Setup test data."""
        self.company = Company.objects.create(name="Test", code="TST")
        
        self.region = Region.objects.create(
            name='East',
            company=self.company
        )
        
        self.fund = TreasuryFund.objects.create(
            company=self.company,
            region=self.region,
            current_balance=Decimal('5000000.00'),
            reorder_level=Decimal('2000000.00')
        )
        
        self.user = User.objects.create_user(username='requester', password='pass123')
    
    def test_payment_summary_generation(self):
        """Test payment summary report generation."""
        # Create payments
        requisition = Requisition.objects.create(
            transaction_id='REQ-002',
            origin_type='hq',
            requesting_user=self.user,
            amount=Decimal('100000.00'),
            purpose='Test'
        )
        
        Payment.objects.create(
            requisition=requisition,
            treasury_fund=self.fund,
            amount=Decimal('100000.00'),
            method='bank_transfer',
            destination='ACC-001',
            status='success'
        )
        
        today = timezone.now().date()
        report = ReportService.generate_payment_summary(
            self.company.id,
            today - timedelta(days=7),
            today
        )
        
        self.assertEqual(report['total_payments'], 1)
        self.assertEqual(report['total_amount'], 100000.00)
        self.assertEqual(report['success_rate'], 100.0)
    
    def test_fund_health_report_generation(self):
        """Test fund health report generation."""
        report = ReportService.generate_fund_health_report(self.company.id)
        
        self.assertEqual(report['total_funds'], 1)
        self.assertEqual(report['total_balance'], 5000000.00)
        self.assertEqual(len(report['fund_details']), 1)
        self.assertEqual(report['fund_details'][0]['status'], 'OK')
    
    def test_variance_analysis_generation(self):
        """Test variance analysis report generation."""
        # Create variance
        VarianceAdjustment.objects.create(
            treasury_fund=self.fund,
            variance_amount=Decimal('5000.00'),
            reason='Gateway discount',
            status='approved'
        )
        
        today = timezone.now().date()
        report = ReportService.generate_variance_analysis(
            self.company.id,
            today - timedelta(days=7),
            today
        )
        
        self.assertEqual(report['total_variances'], 1)
        self.assertEqual(report['total_variance_amount'], 5000.00)
    
    def test_fund_forecast_generation(self):
        """Test replenishment forecast generation."""
        # Create ledger entries for spending pattern
        for i in range(10):
            LedgerEntry.objects.create(
                treasury_fund=self.fund,
                entry_type='debit',
                amount=Decimal('50000.00'),
                description=f'Payment {i}'
            )
        
        forecast = ReportService.generate_replenishment_forecast(self.fund, horizon_days=30)
        
        self.assertIsNotNone(forecast)
        self.assertEqual(forecast.fund, self.fund)
        self.assertFalse(forecast.needs_replenishment)
        self.assertGreater(forecast.confidence_level, 0)
    
    def test_critical_fund_forecast(self):
        """Test forecast for fund nearing reorder."""
        # Set fund close to reorder level
        self.fund.current_balance = Decimal('2100000.00')
        self.fund.save()
        
        # Create heavy spending pattern
        for i in range(20):
            LedgerEntry.objects.create(
                treasury_fund=self.fund,
                entry_type='debit',
                amount=Decimal('100000.00'),
                description=f'Payment {i}'
            )
        
        forecast = ReportService.generate_replenishment_forecast(self.fund, horizon_days=30)
        
        # Should recommend replenishment
        self.assertTrue(forecast.needs_replenishment)
        self.assertGreater(forecast.recommended_replenishment_amount, 0)
    
    def test_report_csv_export(self):
        """Test CSV export."""
        report_data = {
            'period': '2025-11-01 to 2025-11-15',
            'total_payments': 5,
            'total_amount': 50000.00,
            'success_rate': 95.0,
            'by_status': {},
            'by_method': {},
            'by_origin': {}
        }
        
        csv_output = ReportService.export_report_to_csv(report_data, 'payment_summary')
        
        self.assertIsNotNone(csv_output)
        self.assertIn('Payment Summary Report', csv_output)
        self.assertIn('2025-11-01 to 2025-11-15', csv_output)


class PaymentTrackingTestCase(TestCase):
    """Test payment execution tracking."""
    
    def setUp(self):
        """Setup test data."""
        self.company = Company.objects.create(name="Test", code="TST")
        
        self.fund = TreasuryFund.objects.create(
            company=self.company,
            current_balance=Decimal('1000000.00'),
            reorder_level=Decimal('500000.00')
        )
        
        self.user = User.objects.create_user(username='executor', password='pass123')
        
        requisition = Requisition.objects.create(
            transaction_id='REQ-003',
            origin_type='branch',
            requesting_user=self.user,
            amount=Decimal('50000.00'),
            purpose='Test'
        )
        
        self.payment = Payment.objects.create(
            requisition=requisition,
            treasury_fund=self.fund,
            amount=Decimal('50000.00'),
            method='bank_transfer',
            destination='ACC-001',
            status='pending'
        )
    
    def test_payment_tracking_creation(self):
        """Test automatic payment tracking creation."""
        tracking = PaymentTracking.objects.create(
            payment=self.payment,
            current_status='created'
        )
        
        self.assertEqual(tracking.payment, self.payment)
        self.assertEqual(tracking.current_status, 'created')
    
    def test_payment_tracking_status_progression(self):
        """Test payment status progression tracking."""
        tracking = PaymentTracking.objects.create(
            payment=self.payment,
            current_status='created'
        )
        
        # OTP sent
        tracking.current_status = 'otp_sent'
        tracking.otp_sent_at = timezone.now()
        tracking.save()
        
        self.assertEqual(tracking.current_status, 'otp_sent')
        self.assertIsNotNone(tracking.otp_sent_at)
    
    def test_execution_time_calculation(self):
        """Test execution time calculation."""
        tracking = PaymentTracking.objects.create(
            payment=self.payment,
            current_status='created',
            created_at=timezone.now()
        )
        
        # Simulate execution
        import time
        time.sleep(1)
        tracking.execution_completed_at = timezone.now()
        tracking.total_execution_time = tracking.execution_completed_at - tracking.created_at
        tracking.save()
        
        self.assertIsNotNone(tracking.total_execution_time)
        self.assertGreater(tracking.total_execution_time.total_seconds(), 0)


class APIEndpointTestCase(TestCase):
    """Test Phase 6 API endpoints."""
    
    def setUp(self):
        """Setup test client and data."""
        self.client = Client()
        
        self.company = Company.objects.create(name="Test", code="TST")
        
        self.user = User.objects.create_user(username='api_user', password='pass123')
        self.user.profile.company = self.company
        self.user.profile.save()
        
        self.fund = TreasuryFund.objects.create(
            company=self.company,
            current_balance=Decimal('1000000.00'),
            reorder_level=Decimal('500000.00')
        )
    
    def test_dashboard_summary_endpoint(self):
        """Test dashboard summary endpoint."""
        self.client.login(username='api_user', password='pass123')
        
        response = self.client.get(reverse('dashboard-summary'))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('total_funds', data)
        self.assertIn('total_balance', data)
    
    def test_fund_status_endpoint(self):
        """Test fund status endpoint."""
        self.client.login(username='api_user', password='pass123')
        
        response = self.client.get(reverse('dashboard-fund-status'))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('fund_status', data)
    
    def test_alerts_active_endpoint(self):
        """Test active alerts endpoint."""
        self.client.login(username='api_user', password='pass123')
        
        # Create alert
        Alert.objects.create(
            alert_type='fund_critical',
            severity='Critical',
            title='Test Alert',
            message='Test',
            related_fund=self.fund
        )
        
        response = self.client.get(reverse('alert-active'))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('active_alerts', data)
        self.assertEqual(len(data['active_alerts']), 1)
    
    def test_payment_summary_report_endpoint(self):
        """Test payment summary report endpoint."""
        self.client.login(username='api_user', password='pass123')
        
        today = timezone.now().date()
        response = self.client.get(
            reverse('report-payment-summary'),
            {
                'start_date': str(today - timedelta(days=30)),
                'end_date': str(today)
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('total_payments', data)
    
    def test_fund_health_report_endpoint(self):
        """Test fund health report endpoint."""
        self.client.login(username='api_user', password='pass123')
        
        response = self.client.get(reverse('report-fund-health'))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('total_funds', data)
        self.assertIn('fund_details', data)


# ============================================================================
# EXECUTION
# ============================================================================

if __name__ == '__main__':
    import unittest
    
    # Create test suite
    test_classes = [
        DashboardServiceTestCase,
        AlertServiceTestCase,
        ReportServiceTestCase,
        PaymentTrackingTestCase,
        APIEndpointTestCase,
    ]
    
    suite = unittest.TestSuite()
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print("PHASE 6 TEST SUMMARY")
    print("=" * 70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")
    print("=" * 70)
