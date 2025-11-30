from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from settings_manager.models import SystemSetting
from system_maintenance.models import MaintenanceMode

User = get_user_model()


class MaintenanceViewTests(TestCase):
	def setUp(self):
		# create superuser (AbstractUser requires username)
		self.admin = User.objects.create_superuser('admin', email='admin@example.com', password='pass')
		# ensure SystemSetting exists
		self.setting, _ = SystemSetting.objects.get_or_create(
			key='SYSTEM_MAINTENANCE_MODE',
			defaults={
				'display_name': 'System Maintenance Mode',
				'description': 'Toggle basic maintenance mode setting',
				'category': 'general',
				'setting_type': 'boolean',
				'value': 'false',
				'default_value': 'false',
				'is_active': True,
				'editable_by_admin': True,
				'requires_restart': False,
			}
		)
		self.client = Client()
		self.client.force_login(self.admin)

	def test_get_maintenance_page(self):
		resp = self.client.get(reverse('settings_manager:maintenance'))
		self.assertEqual(resp.status_code, 200)
		self.assertContains(resp, 'Maintenance Management')

	def test_create_and_deactivate_session(self):
		# create session
		resp = self.client.post(reverse('settings_manager:maintenance'), {
			'action': 'create_session',
			'reason': 'test',
			'duration_minutes': '10',
		}, follow=True)
		self.assertEqual(resp.status_code, 200)
		active = MaintenanceMode.objects.filter(is_active=True).first()
		self.assertIsNotNone(active)

		# deactivate
		resp = self.client.post(reverse('settings_manager:maintenance'), {
			'action': 'deactivate_session',
			'session_id': str(active.id),
		}, follow=True)
		self.assertEqual(resp.status_code, 200)
		self.assertFalse(MaintenanceMode.objects.filter(is_active=True).exists())

	def test_toggle_setting_and_sync(self):
		# toggle setting to true
		resp = self.client.post(reverse('settings_manager:maintenance'), {'action': 'toggle_setting', 'is_active': 'on'}, follow=True)
		self.assertEqual(resp.status_code, 200)
		self.setting.refresh_from_db()
		self.assertTrue(self.setting.is_active)

		# sync to session should create a MaintenanceMode
		resp = self.client.post(reverse('settings_manager:maintenance'), {'action': 'sync_to_session'}, follow=True)
		self.assertEqual(resp.status_code, 200)
		self.assertTrue(MaintenanceMode.objects.filter(is_active=True).exists())
