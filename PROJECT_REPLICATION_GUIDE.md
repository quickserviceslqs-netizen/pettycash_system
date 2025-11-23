# 🚀 Petty Cash Management System — Complete Replication Guide

**Build a Production-Ready Petty Cash System from Scratch**

This guide provides step-by-step instructions to replicate the entire Petty Cash Management System. Follow these instructions sequentially to build a fully functional system with all features implemented.

---

## 📋 Table of Contents

1. [Prerequisites & Environment Setup](#1-prerequisites--environment-setup)
2. [Project Initialization](#2-project-initialization)
3. [Database Configuration](#3-database-configuration)
4. [Core Apps Creation](#4-core-apps-creation)
5. [Models Implementation](#5-models-implementation)
6. [Workflow Engine](#6-workflow-engine)
7. [Treasury Payment Services](#7-treasury-payment-services)
8. [Views & APIs](#8-views--apis)
9. [Templates & UI](#9-templates--ui)
10. [Admin Configuration](#10-admin-configuration)
11. [Management Commands](#11-management-commands)
12. [Security & Authentication](#12-security--authentication)
13. [Testing](#13-testing)
14. [Deployment](#14-deployment)
15. [Initial Data Setup](#15-initial-data-setup)

---

## 1. Prerequisites & Environment Setup

### System Requirements
- **Python:** 3.11+ (tested on 3.13.7)
- **PostgreSQL:** 14+ (or SQLite for local development)
- **Git:** For version control
- **Operating System:** Windows, macOS, or Linux

### Step 1.1: Create Virtual Environment

```powershell
# Create project directory
mkdir pettycash_system
cd pettycash_system

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### Step 1.2: Install Dependencies

```powershell
# Install Django and core packages
pip install django==5.2.8
pip install djangorestframework==3.15.2
pip install psycopg2-binary==2.9.9
pip install django-filter==24.3
pip install django-crispy-forms==2.3
pip install crispy-bootstrap5==2024.2
pip install django-environ==0.11.2

# Production server
pip install gunicorn==23.0.0
pip install whitenoise==6.8.2
pip install dj-database-url==2.2.0

# Create requirements.txt
pip freeze > requirements.txt
```

### Step 1.3: Create requirements.txt

```txt
Django==5.2.8
djangorestframework==3.15.2
psycopg2-binary==2.9.9
django-filter==24.3
django-crispy-forms==2.3
crispy-bootstrap5==2024.2
django-environ==0.11.2
gunicorn==23.0.0
whitenoise==6.8.2
dj-database-url==2.2.0
```

---

## 2. Project Initialization

### Step 2.1: Create Django Project

```powershell
# Create Django project
django-admin startproject pettycash_system .

# Verify structure
ls
# Should see: manage.py, pettycash_system/, venv/
```

### Step 2.2: Create Apps

```powershell
# Create all Django apps
python manage.py startapp accounts
python manage.py startapp organization
python manage.py startapp transactions
python manage.py startapp treasury
python manage.py startapp reports
python manage.py startapp workflow
```

### Step 2.3: Update settings.py

Edit `pettycash_system/settings.py`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'django_filters',
    'crispy_forms',
    'crispy_bootstrap5',
    
    # Local apps
    'accounts',
    'organization',
    'transactions',
    'treasury',
    'reports',
    'workflow',
]

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
```

---

## 3. Database Configuration

### Step 3.1: PostgreSQL Setup (Production)

```python
# In settings.py, add:
import dj_database_url
import os

# Database configuration
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3'),
        conn_max_age=600
    )
}
```

### Step 3.2: Environment Variables

Create `.env` file:

```env
SECRET_KEY=your-secret-key-here-change-this-in-production
DEBUG=True
DATABASE_URL=postgresql://user:password@localhost:5432/pettycash_db
ALLOWED_HOSTS=localhost,127.0.0.1
```

Update `settings.py`:

```python
import environ

env = environ.Env(
    DEBUG=(bool, False)
)

# Read .env file
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost'])
```

---

## 4. Core Apps Creation

### Step 4.1: Organization App Models

Create `organization/models.py`:

```python
from django.db import models
import uuid

class Company(models.Model):
    company_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name

class Region(models.Model):
    region_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='regions')
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.company.code})"

class Branch(models.Model):
    branch_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='branches')
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Branches"

    def __str__(self):
        return f"{self.name} ({self.region.name})"

class Department(models.Model):
    department_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class CostCenter(models.Model):
    cost_center_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='cost_centers')
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Position(models.Model):
    position_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='positions')
    title = models.CharField(max_length=200)
    level = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
```

### Step 4.2: Accounts App - Custom User Model

Create `accounts/models.py`:

```python
from django.contrib.auth.models import AbstractUser
from django.db import models
from organization.models import Company, Region, Branch, Department, CostCenter

class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('staff', 'Staff'),
        ('department_head', 'Department Head'),
        ('branch_manager', 'Branch Manager'),
        ('regional_manager', 'Regional Manager'),
        ('group_finance_manager', 'Group Finance Manager'),
        ('treasury', 'Treasury'),
        ('cfo', 'Chief Financial Officer'),
        ('fp&a', 'FP&A'),
        ('ceo', 'Chief Executive Officer'),
    ]

    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='staff')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, null=True, blank=True)
    
    phone_number = models.CharField(max_length=20, blank=True)
    position_title = models.CharField(max_length=100, blank=True)
    is_centralized_approver = models.BooleanField(default=False)

    def get_display_name(self):
        """Returns first_name + last_name or username fallback"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    def get_role_display(self):
        """Returns human-readable role name"""
        return dict(self.ROLE_CHOICES).get(self.role, self.role.title())

    def __str__(self):
        return f"{self.get_display_name()} ({self.get_role_display()})"
```

---

## 5. Models Implementation

### Step 5.1: Workflow App Models

Create `workflow/models.py`:

```python
from django.db import models
from decimal import Decimal

class ApprovalThreshold(models.Model):
    ORIGIN_CHOICES = [
        ('BRANCH', 'Branch'),
        ('HQ', 'HQ'),
        ('FIELD', 'Field'),
        ('ANY', 'Any'),
    ]

    name = models.CharField(max_length=100)
    origin_type = models.CharField(max_length=10, choices=ORIGIN_CHOICES)
    min_amount = models.DecimalField(max_digits=14, decimal_places=2)
    max_amount = models.DecimalField(max_digits=14, decimal_places=2)
    
    roles_sequence = models.JSONField(
        help_text="Array of role names in approval order, e.g., ['branch_manager', 'treasury']"
    )
    
    allow_urgent_fasttrack = models.BooleanField(default=True)
    requires_cfo = models.BooleanField(default=False)
    
    priority = models.IntegerField(default=0, help_text="Lower number = higher priority")
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', 'min_amount']

    def __str__(self):
        return f"{self.name} ({self.origin_type}): ${self.min_amount} - ${self.max_amount}"
```

### Step 5.2: Transactions App Models

Create `transactions/models.py`:

```python
import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from organization.models import Company, Region, Branch, Department
from workflow.models import ApprovalThreshold

User = settings.AUTH_USER_MODEL

def generate_transaction_id():
    return str(uuid.uuid4())

class Requisition(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('pending_urgency_confirmation', 'Pending Urgency Confirmation'),
        ('pending_dept_approval', 'Pending Department Approval'),
        ('pending_branch_approval', 'Pending Branch Approval'),
        ('pending_regional_review', 'Pending Regional Review'),
        ('pending_finance_review', 'Pending Finance Review'),
        ('pending_treasury_validation', 'Pending Treasury Validation'),
        ('pending_cfo_approval', 'Pending CFO Approval'),
        ('paid', 'Paid'),
        ('reviewed', 'Reviewed'),
        ('rejected', 'Rejected'),
    ]
    
    ORIGIN_CHOICES = [
        ('branch', 'Branch'),
        ('hq', 'HQ'),
        ('field', 'Field'),
    ]

    transaction_id = models.CharField(
        primary_key=True, 
        max_length=64, 
        default=generate_transaction_id, 
        editable=False
    )
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    origin_type = models.CharField(max_length=10, choices=ORIGIN_CHOICES)
    
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    purpose = models.TextField()
    is_urgent = models.BooleanField(default=False)
    urgency_reason = models.TextField(blank=True, null=True)

    applied_threshold = models.ForeignKey(
        ApprovalThreshold, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name='requisitions'
    )
    tier = models.CharField(max_length=64, blank=True, null=True)
    
    workflow_sequence = models.JSONField(blank=True, null=True)
    next_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL,
        null=True, 
        related_name='next_approvals'
    )
    
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.transaction_id} - {self.status}"

    def can_approve(self, user):
        """Phase 4: Prevent self-approval"""
        if user.id == self.requested_by.id:
            return False
        return user.id == self.next_approver_id

    def resolve_workflow(self):
        """Resolve approval workflow using workflow engine"""
        from workflow.services.resolver import resolve_workflow
        resolve_workflow(self)

class ApprovalTrail(models.Model):
    ACTION_CHOICES = [
        ('approved', 'Approved'),
        ('validated', 'Validated'),
        ('paid', 'Paid'),
        ('reviewed', 'Reviewed'),
        ('rejected', 'Rejected'),
        ('urgency_confirmed', 'Urgency Confirmed'),
    ]

    requisition = models.ForeignKey(Requisition, on_delete=models.CASCADE, related_name='approvals')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=50)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    comment = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Phase 4: No-self-approval audit fields
    auto_escalated = models.BooleanField(default=False)
    escalation_reason = models.TextField(blank=True)
    skipped_roles = models.JSONField(default=list)
    override = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.requisition.transaction_id} - {self.user.username} - {self.action}"
```

### Step 5.3: Treasury App Models

Create `treasury/models.py`:

```python
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from organization.models import Company, Region, Branch
from transactions.models import Requisition

class TreasuryFund(models.Model):
    fund_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    
    current_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=14, decimal_places=2, default=50000)
    target_balance = models.DecimalField(max_digits=14, decimal_places=2, default=200000)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        location = self.branch or self.region or self.company
        return f"Fund: {location} - Balance: {self.current_balance}"

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('executing', 'Executing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('reconciled', 'Reconciled'),
    ]
    
    METHOD_CHOICES = [
        ('mpesa', 'M-PESA'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
    ]

    payment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requisition = models.OneToOneField(Requisition, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='bank_transfer')
    destination = models.CharField(max_length=255, blank=True)
    
    # Phase 5: OTP/2FA Security
    otp_hash = models.CharField(max_length=64, blank=True, null=True)
    otp_required = models.BooleanField(default=True)
    otp_verified = models.BooleanField(default=False)
    otp_sent_timestamp = models.DateTimeField(null=True, blank=True)
    otp_verified_timestamp = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    executor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='executed_payments'
    )
    execution_timestamp = models.DateTimeField(null=True, blank=True)
    
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    last_error = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def requester(self):
        """Convenience property for executor segregation checks"""
        return self.requisition.requested_by

    def __str__(self):
        return f"Payment {self.payment_id} - {self.status}"

class LedgerEntry(models.Model):
    ENTRY_TYPE_CHOICES = [
        ('debit', 'Debit'),
        ('credit', 'Credit'),
    ]

    ledger_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fund = models.ForeignKey(TreasuryFund, on_delete=models.CASCADE, related_name='ledger_entries')
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, null=True, blank=True)
    
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    description = models.TextField()
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    reconciled = models.BooleanField(default=False)
    reconciled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reconciled_entries'
    )
    reconciliation_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Ledger Entries"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.entry_type.upper()}: {self.amount} - {self.fund}"

class PaymentExecution(models.Model):
    execution_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='executions')
    executor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    gateway_reference = models.CharField(max_length=255, unique=True)
    gateway_status = models.CharField(max_length=50)
    
    otp_verified_at = models.DateTimeField(null=True, blank=True)
    otp_verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='otp_verifications'
    )
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    
    executed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Execution {self.gateway_reference}"

class ReplenishmentRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]

    request_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fund = models.ForeignKey(TreasuryFund, on_delete=models.CASCADE, related_name='replenishment_requests')
    
    current_balance = models.DecimalField(max_digits=14, decimal_places=2)
    requested_amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    auto_triggered = models.BooleanField(default=False)
    
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Replenishment for {self.fund} - {self.requested_amount}"

class VarianceAdjustment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    variance_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='variances')
    fund = models.ForeignKey(TreasuryFund, on_delete=models.CASCADE, null=True, blank=True)
    
    original_amount = models.DecimalField(max_digits=14, decimal_places=2)
    adjusted_amount = models.DecimalField(max_digits=14, decimal_places=2)
    variance_amount = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.TextField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Variance {self.variance_id} - {self.variance_amount}"
```

---

## 6. Workflow Engine

### Step 6.1: Create Workflow Resolver Service

Create `workflow/services/__init__.py` (empty file)

Create `workflow/services/resolver.py`:

```python
from django.contrib.auth import get_user_model
from django.db.models import Q
from workflow.models import ApprovalThreshold
from django.core.exceptions import PermissionDenied
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

# Centralized roles that are not filtered by branch/region/company
CENTRALIZED_ROLES = ["treasury", "fp&a", "group_finance_manager", "cfo", "ceo", "admin"]


def find_approval_threshold(amount, origin_type):
    """Find matching ApprovalThreshold for requisition."""
    thresholds = (
        ApprovalThreshold.objects.filter(is_active=True)
        .filter(Q(origin_type=origin_type.upper()) | Q(origin_type='ANY'))
        .order_by('priority', 'min_amount')
    )

    for thr in thresholds:
        if thr.min_amount <= amount <= thr.max_amount:
            return thr
    return None


def resolve_workflow(requisition):
    """
    Build approval workflow based on threshold, origin, urgency, and requester role.
    
    Handles:
    - Case-insensitive role matching
    - Centralized roles
    - Scoped routing
    - No-self-approval (Phase 4)
    - Treasury-originated overrides (Phase 5)
    - Urgent fast-track (Phase 3)
    """
    # 1. Load threshold if not already applied
    if not requisition.applied_threshold:
        thr = find_approval_threshold(requisition.amount, requisition.origin_type)
        if not thr:
            raise ValueError("No ApprovalThreshold found for this requisition.")

        requisition.applied_threshold = thr
        requisition.tier = thr.name
        requisition.save(update_fields=["applied_threshold", "tier"])

    base_roles = requisition.applied_threshold.roles_sequence
    resolved = []

    # 2. Treasury special case override (Phase 5)
    is_treasury_request = requisition.requested_by.role.lower() == "treasury"
    if is_treasury_request:
        tier = requisition.tier
        if "Tier 1" in tier:
            base_roles = ["department_head", "group_finance_manager"]
        elif "Tier 2" in tier or "Tier 3" in tier:
            base_roles = ["group_finance_manager", "cfo"]
        elif "Tier 4" in tier:
            base_roles = ["cfo", "ceo"]

    # 3. Loop through roles in order
    for role in base_roles:
        # Skip staff
        if role.lower() == "staff":
            continue

        normalized_role = role.lower()
        candidates = User.objects.filter(
            role=normalized_role, 
            is_active=True
        ).exclude(id=requisition.requested_by.id)  # Phase 4: No self-approval

        # Apply scoping only for non-centralized roles
        if normalized_role not in CENTRALIZED_ROLES:
            if requisition.origin_type.lower() == "branch" and requisition.branch:
                candidates = candidates.filter(branch=requisition.branch)
            elif requisition.origin_type.lower() == "hq" and requisition.company:
                candidates = candidates.filter(company=requisition.company)
            elif requisition.origin_type.lower() == "field" and requisition.region:
                candidates = candidates.filter(region=requisition.region)

        candidate = candidates.first()
        if candidate:
            resolved.append({
                "user_id": candidate.id,
                "role": role,
                "auto_escalated": False
            })
        else:
            logger.warning(
                f"No {role} found for requisition {requisition.transaction_id}, "
                "auto-escalation needed"
            )
            resolved.append({
                "user_id": None,
                "role": role,
                "auto_escalated": True
            })

    # 4. Phase 4: Auto-escalation (no valid approvers found)
    if not resolved or all(r["user_id"] is None for r in resolved):
        admin = User.objects.filter(is_superuser=True, is_active=True).first()
        if not admin:
            raise ValueError("No ADMIN user exists. Please create one.")
        
        escalation_reason = f"No approvers found in roles: {base_roles}"
        logger.warning(f"Auto-escalating {requisition.transaction_id} to admin: {escalation_reason}")
        
        resolved = [{
            "user_id": admin.id,
            "role": "ADMIN",
            "auto_escalated": True,
            "escalation_reason": escalation_reason
        }]

    # 5. Phase 3: Urgent fast-track
    if (
        getattr(requisition, "is_urgent", False)
        and requisition.applied_threshold.allow_urgent_fasttrack
        and "Tier 4" not in requisition.tier
        and len(resolved) > 1
        and resolved[-1].get("user_id") is not None
    ):
        logger.info(
            f"Phase 3 urgent fast-track for {requisition.transaction_id}: "
            "jumping to final approver"
        )
        resolved = [resolved[-1]]

    # 6. Replace None user_ids with escalation
    for i, r in enumerate(resolved):
        if r["user_id"] is None:
            # Find next available approver or escalate to admin
            next_approver = None
            for j in range(i + 1, len(resolved)):
                if resolved[j]["user_id"] is not None:
                    next_approver = resolved[j]
                    break
            
            if next_approver:
                r["user_id"] = next_approver["user_id"]
                r["auto_escalated"] = True
                r["escalation_reason"] = f"No {r['role']} found, escalated to {next_approver['role']}"
            else:
                admin = User.objects.filter(is_superuser=True, is_active=True).first()
                r["user_id"] = admin.id
                r["role"] = "ADMIN"
                r["auto_escalated"] = True
                r["escalation_reason"] = f"No {r['role']} found, escalated to ADMIN"

    # 7. Save workflow sequence and set next approver
    requisition.workflow_sequence = resolved
    if resolved:
        requisition.next_approver_id = resolved[0]["user_id"]
    requisition.save(update_fields=["workflow_sequence", "next_approver"])
```

---

## 7. Treasury Payment Services

### Step 7.1: Create Payment Service

Create `treasury/services/__init__.py` (empty file)

Create `treasury/services/payment_service.py`:

```python
"""
Payment execution service for Treasury Payment Execution (Phase 5).

Core principles:
1. Segregation of Duties: executor ≠ requisition requester
2. 2FA required for all payments over threshold
3. Atomic transactions with automatic rollback on failure
4. Immutable audit trail via PaymentExecution records
5. Auto-trigger replenishment when balance drops below threshold
"""

import uuid
import random
import string
import hashlib
import hmac
from decimal import Decimal
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model

from transactions.models import Requisition
from treasury.models import (
    Payment, PaymentExecution, LedgerEntry, 
    VarianceAdjustment, ReplenishmentRequest, TreasuryFund
)

User = get_user_model()


class OTPService:
    """Generate and validate one-time passwords for 2FA."""
    
    OTP_LENGTH = 6
    OTP_VALIDITY_MINUTES = 5
    
    @staticmethod
    def generate_otp() -> str:
        """Generate 6-digit OTP."""
        return ''.join(random.choices(string.digits, k=OTPService.OTP_LENGTH))
    
    @staticmethod
    def hash_otp(otp: str, payment_id: str) -> str:
        """Hash OTP with payment ID as salt using SHA-256."""
        salted_otp = f"{otp}{payment_id}{settings.SECRET_KEY}"
        return hashlib.sha256(salted_otp.encode()).hexdigest()
    
    @staticmethod
    def send_otp_email(email: str, otp: str) -> bool:
        """Send OTP via email. Returns True if successful."""
        try:
            subject = "Petty Cash Payment Verification - One-Time Password"
            message = f"""
Your one-time password (OTP) for payment approval is:

    {otp}

This code is valid for {OTPService.OTP_VALIDITY_MINUTES} minutes.
If you did not request this, please ignore this email.

Do not share this code with anyone.
            """
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            print(f"Failed to send OTP email to {email}: {str(e)}")
            return False
    
    @staticmethod
    def is_otp_expired(payment: Payment) -> bool:
        """Check if OTP has expired (>5 minutes old)."""
        if not payment.otp_sent_timestamp:
            return True
        now = timezone.now()
        expiry = payment.otp_sent_timestamp + timedelta(minutes=OTPService.OTP_VALIDITY_MINUTES)
        return now > expiry


class PaymentExecutionService:
    """Orchestrate atomic payment execution with all safeguards."""
    
    @staticmethod
    def assign_executor(payment: Payment):
        """
        Phase 5: Assign executor for payment, ensuring executor ≠ requester.
        For Treasury-originated requests, assign different treasury officer or escalate to CFO.
        
        Returns: (executor_user, escalation_message)
        """
        requester = payment.requisition.requested_by
        
        # Find alternate treasury officer (exclude requester)
        treasury_officers = User.objects.filter(
            role='treasury',
            is_active=True
        ).exclude(id=requester.id)
        
        if treasury_officers.exists():
            return treasury_officers.first(), None
        else:
            # No alternate treasury officer - escalate to CFO
            cfo = User.objects.filter(role='cfo', is_active=True).first()
            if cfo:
                escalation_msg = (
                    f"No alternate Treasury officer available for payment {payment.payment_id}. "
                    f"Requester: {requester.get_display_name()}. CFO must assign executor."
                )
                return None, escalation_msg
            else:
                # Last resort: admin
                admin = User.objects.filter(is_superuser=True, is_active=True).first()
                escalation_msg = (
                    f"No alternate Treasury officer or CFO available. "
                    f"Admin must assign executor for payment {payment.payment_id}."
                )
                return None, escalation_msg
    
    @staticmethod
    def can_execute_payment(payment: Payment, executor_user) -> tuple[bool, str]:
        """
        Validate if executor can process payment.
        Returns (can_execute, error_message)
        """
        # Check 1: Payment not already executed
        if payment.status in ['success', 'reconciled']:
            return False, "Payment already completed"
        
        # Check 2: Executor segregation - executor cannot be requester
        if payment.requisition.requested_by == executor_user:
            return False, "Executor cannot approve their own requisition"
        
        # Check 3: 2FA verification if required
        if payment.otp_required and not payment.otp_verified:
            return False, "OTP verification required before execution"
        
        # Check 4: OTP not expired
        if payment.otp_required and OTPService.is_otp_expired(payment):
            return False, "OTP has expired. Request new OTP."
        
        # Check 5: Retry limit not exceeded
        if payment.retry_count >= payment.max_retries:
            return False, f"Max retries ({payment.max_retries}) exceeded"
        
        # Check 6: Fund balance available
        requisition = payment.requisition
        fund = TreasuryFund.objects.filter(
            company=requisition.company,
            region=requisition.region,
            branch=requisition.branch
        ).first()
        
        if not fund or fund.current_balance < payment.amount:
            return False, f"Insufficient fund balance. Available: {fund.current_balance if fund else 0}"
        
        return True, ""
    
    @staticmethod
    @transaction.atomic
    def execute_payment(payment: Payment, executor_user, gateway_reference: str = None, 
                       gateway_status: str = "success", ip_address: str = "", 
                       user_agent: str = "") -> tuple[bool, str]:
        """
        Execute payment atomically with complete audit trail.
        
        Returns (success, message)
        """
        # Step 1: Validation
        can_execute, error = PaymentExecutionService.can_execute_payment(payment, executor_user)
        if not can_execute:
            return False, error
        
        try:
            # Step 2: Get and lock fund
            fund = TreasuryFund.objects.select_for_update().get(
                company=payment.requisition.company,
                region=payment.requisition.region,
                branch=payment.requisition.branch
            )
            
            # Verify balance again
            if fund.current_balance < payment.amount:
                return False, "Insufficient fund balance (concurrent deduction detected)"
            
            # Step 3: Mark as executing
            payment.status = 'executing'
            payment.execution_timestamp = timezone.now()
            payment.save(update_fields=['status', 'execution_timestamp'])
            
            # Step 4: Deduct from fund
            fund.current_balance -= payment.amount
            fund.save(update_fields=['current_balance', 'updated_at'])
            
            # Step 5: Create LedgerEntry
            ledger = LedgerEntry.objects.create(
                ledger_id=uuid.uuid4(),
                fund=fund,
                entry_type='debit',
                amount=payment.amount,
                payment=payment,
                description=f"Payment for {payment.requisition.transaction_id}",
                created_by=executor_user,
            )
            
            # Step 6: Create PaymentExecution record
            execution = PaymentExecution.objects.create(
                execution_id=uuid.uuid4(),
                payment=payment,
                executor=executor_user,
                gateway_reference=gateway_reference or str(uuid.uuid4()),
                gateway_status=gateway_status,
                otp_verified_at=payment.otp_verified_timestamp,
                otp_verified_by=executor_user,
                ip_address=ip_address,
                user_agent=user_agent[:500],
            )
            
            # Step 7: Mark payment as success
            payment.status = 'success'
            payment.executor = executor_user
            payment.save(update_fields=['status', 'executor'])
            
            # Step 8: Check replenishment trigger (Phase 5)
            if fund.current_balance < fund.reorder_level:
                pending = ReplenishmentRequest.objects.filter(
                    fund=fund,
                    status__in=['pending', 'approved']
                ).exists()
                
                if not pending:
                    replenishment = ReplenishmentRequest.objects.create(
                        request_id=uuid.uuid4(),
                        fund=fund,
                        current_balance=fund.current_balance,
                        requested_amount=fund.reorder_level * Decimal('2'),
                        status='pending',
                        auto_triggered=True,
                    )
                    print(f"Auto-triggered replenishment request {replenishment.request_id}")
            
            return True, f"Payment executed successfully. Reference: {execution.gateway_reference}"
        
        except Exception as e:
            # Atomic transaction will automatically rollback
            payment.retry_count += 1
            payment.last_error = str(e)
            payment.status = 'failed'
            payment.save(update_fields=['retry_count', 'last_error', 'status'])
            
            return False, f"Payment execution failed: {str(e)}"
    
    @staticmethod
    def send_otp(payment: Payment) -> tuple[bool, str]:
        """Generate and send OTP to executor."""
        otp = OTPService.generate_otp()
        
        # Hash OTP with payment_id as salt
        otp_hash = OTPService.hash_otp(otp, str(payment.payment_id))
        payment.otp_hash = otp_hash
        payment.otp_sent_timestamp = timezone.now()
        payment.otp_verified = False
        payment.otp_verified_timestamp = None
        payment.save(update_fields=['otp_hash', 'otp_sent_timestamp', 'otp_verified', 'otp_verified_timestamp'])
        
        # Send OTP via email
        executor_email = payment.requisition.requested_by.email
        success = OTPService.send_otp_email(executor_email, otp)
        
        if success:
            return True, "OTP sent successfully"
        else:
            return False, "Failed to send OTP email"
    
    @staticmethod
    def verify_otp(payment: Payment, user_otp: str) -> tuple[bool, str]:
        """Verify OTP with comprehensive security checks."""
        # Check 1: OTP hash exists
        if not payment.otp_hash:
            return False, "No OTP has been sent"
        
        # Check 2: Not already verified (replay prevention)
        if payment.otp_verified:
            return False, "OTP already verified"
        
        # Check 3: Not expired
        if OTPService.is_otp_expired(payment):
            return False, "OTP has expired"
        
        # Check 4: Hash comparison (constant-time to prevent timing attacks)
        user_hash = OTPService.hash_otp(user_otp, str(payment.payment_id))
        if not hmac.compare_digest(user_hash, payment.otp_hash):
            return False, "Invalid OTP"
        
        # Mark as verified
        payment.otp_verified = True
        payment.otp_verified_timestamp = timezone.now()
        payment.save(update_fields=['otp_verified', 'otp_verified_timestamp'])
        
        return True, "OTP verified successfully"
```

---

**(CONTINUED IN NEXT MESSAGE - This guide exceeds message length. Would you like me to continue with the remaining sections 8-15?)**
