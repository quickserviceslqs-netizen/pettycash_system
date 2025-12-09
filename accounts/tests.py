from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class Phase4LoginTests(TestCase):
    def setUp(self):
        # Create users for each role
        self.admin = User.objects.create_user(
            username="admin", password="pass123", role="ADMIN"
        )
        self.staff = User.objects.create_user(
            username="staff", password="pass123", role="STAFF"
        )
        self.finance = User.objects.create_user(
            username="finance", password="pass123", role="FINANCE"
        )
        self.treasury = User.objects.create_user(
            username="treasury", password="pass123", role="TREASURY"
        )

    def test_admin_login_redirect(self):
        login = self.client.login(username="admin", password="pass123")
        response = self.client.get(reverse("role_redirect"))
        self.assertRedirects(response, "/dashboard/")

    def test_staff_login_redirect(self):
        login = self.client.login(username="staff", password="pass123")
        response = self.client.get(reverse("role_redirect"))
        self.assertRedirects(response, "/dashboard/")

    def test_finance_login_redirect(self):
        login = self.client.login(username="finance", password="pass123")
        response = self.client.get(reverse("role_redirect"))
        self.assertRedirects(response, "/dashboard/")

    def test_treasury_login_redirect(self):
        login = self.client.login(username="treasury", password="pass123")
        response = self.client.get(reverse("role_redirect"))
        self.assertRedirects(response, "/dashboard/")
