from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from organization.models import Company, Region, Branch, Department, CostCenter
from transactions.forms import RequisitionForm


class AttachmentValidationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='TestCo', code='TC')
        self.region = Region.objects.create(name='Reg', code='R', company=self.company)
        self.branch = Branch.objects.create(name='Branch', code='B', region=self.region)
        self.department = Department.objects.create(name='Dept', branch=self.branch)
        self.cost_center = CostCenter.objects.create(name='CC1', department=self.department)

    def test_pdf_attachment_allowed_when_settings_use_no_dot_prefix(self):
        data = {
            'origin_type': 'branch',
            'company': self.company.id,
            'region': self.region.id,
            'branch': self.branch.id,
            'department': self.department.id,
            'cost_center': self.cost_center.id,
            'amount': '1000.00',
            'purpose': 'Office items',
            'is_urgent': False,
            'urgency_reason': '',
            'is_draft': False,
        }
        # Simulate PDF upload
        files = {
            'receipt': SimpleUploadedFile('sample.pdf', b'%PDF-1.4\n%test', content_type='application/pdf')
        }
        form = RequisitionForm(data=data, files=files)
        self.assertTrue(form.is_valid(), f"Form should be valid for PDF attachment; errors: {form.errors}")

    def test_spoofed_pdf_extension_rejected_when_content_type_mismatch(self):
        data = {
            'origin_type': 'branch',
            'company': self.company.id,
            'region': self.region.id,
            'branch': self.branch.id,
            'department': self.department.id,
            'cost_center': self.cost_center.id,
            'amount': '1000.00',
            'purpose': 'Office items',
            'is_urgent': False,
            'urgency_reason': '',
            'is_draft': False,
        }
        # Spoofed: .pdf extension but content-type is text/plain
        files = {
            'receipt': SimpleUploadedFile('sample.pdf', b'test', content_type='text/plain')
        }
        form = RequisitionForm(data=data, files=files)
        self.assertFalse(form.is_valid(), "Form should reject a file where content_type doesn't match allowed types even if extension matches")

    def test_no_extension_but_content_type_allows_upload(self):
        data = {
            'origin_type': 'branch',
            'company': self.company.id,
            'region': self.region.id,
            'branch': self.branch.id,
            'department': self.department.id,
            'cost_center': self.cost_center.id,
            'amount': '1000.00',
            'purpose': 'Office items',
            'is_urgent': False,
            'urgency_reason': '',
            'is_draft': False,
        }
        # No extension in filename but content_type indicates image/jpeg
        files = {
            'receipt': SimpleUploadedFile('sample', b'\xff\xd8\xff', content_type='image/jpeg')
        }
        form = RequisitionForm(data=data, files=files)
        self.assertTrue(form.is_valid(), f"Form should accept file with no extension if content_type indicates allowed image type; errors: {form.errors}")
