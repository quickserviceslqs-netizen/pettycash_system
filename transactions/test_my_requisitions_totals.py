from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal

from organization.models import Company, Region, Branch, Department
from django.contrib.auth import get_user_model
from transactions.models import Requisition

User = get_user_model()


class MyRequisitionsTotalsTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Corp", code="TC")
        self.region = Region.objects.create(name="North", code="N", company=self.company)
        self.branch = Branch.objects.create(name="Branch A", code="BA", region=self.region)
        self.department = Department.objects.create(name="Finance", branch=self.branch)

        self.user = User.objects.create_user(
            username="req_user",
            password="pass123",
            role="staff",
            company=self.company,
            branch=self.branch,
            is_active=True,
        )
        # Ensure transactions App exists and user is assigned to it
        from accounts.models import App
        app, _ = App.objects.get_or_create(name='transactions', defaults={'display_name': 'Transactions', 'url': '/transactions/'})
        self.user.assigned_apps.add(app)
        # Give the user permission to view requisitions
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(Requisition)
        perm = Permission.objects.get(codename='view_requisition', content_type=ct)
        self.user.user_permissions.add(perm)
        self.user.is_staff = True
        self.user.save()

        # Create a draft requisition (should NOT be included in total amount)
        Requisition.objects.create(
            requested_by=self.user,
            origin_type="branch",
            company=self.company,
            branch=self.branch,
            department=self.department,
            amount=Decimal("100.00"),
            purpose="Draft",
            status="draft",
        )

        # Create a pending requisition (should be included)
        Requisition.objects.create(
            requested_by=self.user,
            origin_type="branch",
            company=self.company,
            branch=self.branch,
            department=self.department,
            amount=Decimal("200.00"),
            purpose="Pending",
            status="pending",
        )

    def test_total_amount_excludes_drafts(self):
        client = Client()
        client.login(username="req_user", password="pass123")

        response = client.get(reverse('transactions:my-requisitions'))
        self.assertEqual(response.status_code, 200)
        metrics = response.context['metrics']
        # Draft should not be included — total_amount should equal 200.00
        self.assertEqual(metrics['total_amount'], Decimal('200.00'))
        # Total count should include drafts (2)
        self.assertEqual(metrics['total'], 2)
        # Drafts count should be 1
        self.assertEqual(metrics['drafts'], 1)
