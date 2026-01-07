# 🚀 Petty Cash Management System — Replication Guide (Part 2)

**Continuation from Part 1: Sections 8-15**

---

## 8. Views & APIs

### Step 8.1: Accounts Views

Create `accounts/views.py`:

```python
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

# Role access mapping
ROLE_ACCESS = {
    "admin": ["transactions", "treasury", "workflow", "reports"],
    "staff": ["transactions"],
    "treasury": ["treasury", "workflow", "transactions"],
    "fp&a": ["transactions", "reports"],
    "department_head": ["workflow"],
    "branch_manager": ["workflow"],
    "regional_manager": ["workflow", "reports"],
    "group_finance_manager": ["workflow", "reports"],
    "cfo": ["reports"],
    "ceo": ["reports"],
}

APPROVER_ROLES = {
    "admin", "treasury", "fp&a", "department_head",
    "branch_manager", "regional_manager", "group_finance_manager", "cfo",
}

@login_required
def role_based_redirect(request):
    """Redirect all users to dashboard after login."""
    return redirect("dashboard")

@login_required
def dashboard(request):
    """Display dashboard with accessible apps and pending approvals."""
    from transactions.models import Requisition, ApprovalTrail
    from treasury.models import Payment
    
    user = request.user
    user_role = getattr(user, "role", "").lower().strip()
    
    apps = ROLE_ACCESS.get(user_role, [])
    navigation = [{"name": app.capitalize(), "url": f"/{app}/"} for app in apps]
    
    # Dashboard stats
    total_transactions_pending = Requisition.objects.filter(
        status__startswith="pending"
    ).count()
    
    workflow_overdue = ApprovalTrail.objects.filter(
        requisition__status="pending",
        requisition__next_approver__isnull=False
    ).count()
    
    # Pending approvals for approvers
    if user_role in APPROVER_ROLES:
        pending_for_user = Requisition.objects.filter(
            status="pending",
            next_approver=user
        ).exclude(requested_by=user)
        show_pending_section = pending_for_user.exists()
    else:
        pending_for_user = Requisition.objects.none()
        show_pending_section = False
    
    context = {
        "user": user,
        "navigation": navigation,
        "total_transactions_pending": total_transactions_pending,
        "workflow_overdue": workflow_overdue,
        "pending_for_user": pending_for_user,
        "show_pending_section": show_pending_section,
    }
    
    return render(request, "accounts/dashboard.html", context)
```

### Step 8.2: Transactions Views

Create `transactions/views.py`:

```python
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.utils import timezone
from django.db import transaction

from .models import Requisition, ApprovalTrail
from treasury.models import Payment
from django.contrib.auth import get_user_model

User = get_user_model()

@login_required
def transactions_home(request):
    """Main transactions page showing user's requisitions and pending approvals."""
    user = request.user
    
    APPROVER_ROLES = [
        "branch_manager", "regional_manager", "department_head",
        "group_finance_manager", "treasury", "cfo", "admin", "ceo",
    ]
    is_approver = user.role.lower() in APPROVER_ROLES
    
    my_requisitions = Requisition.objects.filter(requested_by=user).order_by('-created_at')
    
    if is_approver:
        pending_for_me = Requisition.objects.filter(
            status__in=["pending", "pending_urgency_confirmation"],
            next_approver=user
        ).exclude(requested_by=user).order_by('-created_at')
        show_pending_section = pending_for_me.exists()
    else:
        pending_for_me = Requisition.objects.none()
        show_pending_section = False
    
    context = {
        "user": user,
        "is_approver": is_approver,
        "requisitions": my_requisitions,
        "pending_for_me": pending_for_me,
        "show_pending_section": show_pending_section,
    }
    return render(request, "transactions/home.html", context)

@login_required
def requisition_detail(request, requisition_id):
    """View requisition details with approval trail."""
    requisition = get_object_or_404(Requisition, transaction_id=requisition_id)
    can_act = requisition.can_approve(request.user)
    
    approval_trail = ApprovalTrail.objects.filter(
        requisition=requisition
    ).select_related('user').order_by('timestamp')
    
    context = {
        "requisition": requisition,
        "can_act": can_act,
        "user": request.user,
        "approval_trail": approval_trail,
    }
    return render(request, "transactions/requisition_detail.html", context)

@login_required
def create_requisition(request):
    """Create new requisition."""
    from .forms import RequisitionForm
    
    if request.method == "POST":
        form = RequisitionForm(request.POST)
        if form.is_valid():
            requisition = form.save(commit=False)
            requisition.requested_by = request.user
            
            if requisition.is_urgent:
                requisition.status = "pending_urgency_confirmation"
            else:
                requisition.status = "pending"
            
            requisition.save()
            
            try:
                requisition.resolve_workflow()
            except Exception as e:
                messages.error(request, f"Error creating requisition: {str(e)}")
                requisition.delete()
                return redirect("transactions-home")
            
            messages.success(request, f"Requisition {requisition.transaction_id} created successfully.")
            return redirect("transactions-home")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RequisitionForm()
    
    return render(request, "transactions/create_requisition.html", {"form": form})

@login_required
@transaction.atomic
def approve_requisition(request, requisition_id):
    """Approve a requisition."""
    try:
        requisition = Requisition.objects.select_for_update().get(
            transaction_id=requisition_id
        )
    except Requisition.DoesNotExist:
        messages.error(request, "Requisition not found.")
        return redirect("transactions-home")
    
    if not requisition.can_approve(request.user):
        return HttpResponseForbidden("You cannot approve this requisition.")
    
    # Create approval trail
    ApprovalTrail.objects.create(
        requisition=requisition,
        user=request.user,
        role=request.user.role,
        action="approved",
        comment=request.POST.get("comment", ""),
        timestamp=timezone.now(),
        auto_escalated=False,
    )
    
    # Move to next approver or mark as reviewed
    workflow_seq = requisition.workflow_sequence or []
    if len(workflow_seq) > 1:
        workflow_seq.pop(0)
        next_user_id = workflow_seq[0]["user_id"]
        requisition.next_approver = get_object_or_404(User, id=next_user_id)
        requisition.workflow_sequence = workflow_seq
        requisition.save(update_fields=["next_approver", "workflow_sequence"])
        messages.success(request, f"Requisition approved. Moved to next approver.")
    else:
        requisition.status = "reviewed"
        requisition.next_approver = None
        requisition.workflow_sequence = []
        requisition.save(update_fields=["status", "next_approver", "workflow_sequence"])
        
        # Create Payment record
        Payment.objects.get_or_create(
            requisition=requisition,
            defaults={
                'amount': requisition.amount,
                'method': 'bank_transfer',
                'status': 'pending',
                'otp_required': True,
            }
        )
        messages.success(request, f"Requisition fully approved! Ready for payment.")
    
    return redirect("transactions-home")

@login_required
@transaction.atomic
def reject_requisition(request, requisition_id):
    """Reject a requisition."""
    try:
        requisition = Requisition.objects.select_for_update().get(
            transaction_id=requisition_id
        )
    except Requisition.DoesNotExist:
        messages.error(request, "Requisition not found.")
        return redirect("transactions-home")
    
    if not requisition.can_approve(request.user):
        return HttpResponseForbidden("You cannot reject this requisition.")
    
    ApprovalTrail.objects.create(
        requisition=requisition,
        user=request.user,
        role=request.user.role,
        action="rejected",
        comment=request.POST.get("comment", ""),
        timestamp=timezone.now(),
    )
    
    requisition.status = "rejected"
    requisition.save(update_fields=["status"])
    
    messages.success(request, "Requisition rejected.")
    return redirect("transactions-home")

@login_required
@transaction.atomic
def confirm_urgency(request, requisition_id):
    """First approver confirms urgency for fast-track."""
    requisition = get_object_or_404(Requisition, transaction_id=requisition_id)
    
    if requisition.status != 'pending_urgency_confirmation':
        messages.error(request, "This requisition is not pending urgency confirmation.")
        return redirect("requisition-detail", requisition_id=requisition_id)
    
    if not requisition.can_approve(request.user):
        return HttpResponseForbidden("You cannot confirm urgency for this requisition.")
    
    # Create urgency_confirmed trail entry
    ApprovalTrail.objects.create(
        requisition=requisition,
        user=request.user,
        role=request.user.role,
        action="urgency_confirmed",
        comment="Urgency confirmed by first approver",
        timestamp=timezone.now(),
    )
    
    # Continue with approval
    return approve_requisition(request, requisition_id)
```

### Step 8.3: Create Requisition Form

Create `transactions/forms.py`:

```python
from django import forms
from .models import Requisition

class RequisitionForm(forms.ModelForm):
    class Meta:
        model = Requisition
        fields = [
            'origin_type', 'company', 'region', 'branch', 'department',
            'amount', 'purpose', 'is_urgent', 'urgency_reason'
        ]
        widgets = {
            'purpose': forms.Textarea(attrs={'rows': 4}),
            'urgency_reason': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        is_urgent = cleaned_data.get('is_urgent')
        urgency_reason = cleaned_data.get('urgency_reason')
        
        if is_urgent and not urgency_reason:
            raise forms.ValidationError("Urgency reason is required for urgent requests.")
        
        return cleaned_data
```

### Step 8.4: URL Configuration

Create `accounts/urls.py`:

```python
from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('redirect/', views.role_based_redirect, name='role-based-redirect'),
]
```

Create `transactions/urls.py`:

```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.transactions_home, name='transactions-home'),
    path('create/', views.create_requisition, name='create-requisition'),
    path('<str:requisition_id>/', views.requisition_detail, name='requisition-detail'),
    path('<str:requisition_id>/approve/', views.approve_requisition, name='approve-requisition'),
    path('<str:requisition_id>/reject/', views.reject_requisition, name='reject-requisition'),
    path('<str:requisition_id>/confirm-urgency/', views.confirm_urgency, name='confirm-urgency'),
]
```

Update `pettycash_system/urls.py`:

```python
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('transactions/', include('transactions.urls')),
    path('', RedirectView.as_view(url='/accounts/dashboard/', permanent=False)),
]
```

---

## 9. Templates & UI

### Step 9.1: Create Base Template

Create `templates/base.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Petty Cash System{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">Petty Cash System</a>
            {% if user.is_authenticated %}
            <div class="navbar-nav ms-auto">
                <span class="navbar-text text-white me-3">
                    {{ user.get_display_name }}
                    <span class="badge bg-light text-dark">{{ user.get_role_display }}</span>
                </span>
                <a class="nav-link" href="/admin/logout/">Logout</a>
            </div>
            {% endif %}
        </div>
    </nav>

    <div class="container mt-4">
        {% if messages %}
            {% for message in messages %}
            <div class="alert alert-{{ message.tags }} alert-dismissible fade show" role="alert">
                {{ message }}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
            {% endfor %}
        {% endif %}

        {% block content %}{% endblock %}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```

### Step 9.2: Create Dashboard Template

Create `templates/accounts/dashboard.html`:

```html
{% extends "base.html" %}

{% block title %}Dashboard{% endblock %}

{% block content %}
<h2>Welcome, {{ user.get_display_name }}</h2>
<p>Role: <strong>{{ user.get_role_display }}</strong></p>

<div class="row mt-4">
    <div class="col-md-4">
        <div class="card text-white bg-primary mb-3">
            <div class="card-body">
                <h5 class="card-title">Pending Transactions</h5>
                <h2>{{ total_transactions_pending }}</h2>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card text-white bg-warning mb-3">
            <div class="card-body">
                <h5 class="card-title">Workflow Overdue</h5>
                <h2>{{ workflow_overdue }}</h2>
            </div>
        </div>
    </div>
</div>

{% if show_pending_section %}
<h3 class="mt-4">Pending Your Approval</h3>
<table class="table table-striped">
    <thead>
        <tr>
            <th>ID</th>
            <th>Requester</th>
            <th>Amount</th>
            <th>Purpose</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody>
        {% for req in pending_for_user %}
        <tr>
            <td>{{ req.transaction_id }}</td>
            <td>{{ req.requested_by.get_display_name }}</td>
            <td>${{ req.amount }}</td>
            <td>{{ req.purpose|truncatewords:10 }}</td>
            <td>
                <a href="{% url 'requisition-detail' req.transaction_id %}" class="btn btn-sm btn-primary">View</a>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endif %}

<h3 class="mt-4">Quick Links</h3>
<ul>
    {% for app in navigation %}
    <li><a href="{{ app.url }}">{{ app.name }}</a></li>
    {% endfor %}
</ul>
{% endblock %}
```

### Step 9.3: Create Transactions Home Template

Create `templates/transactions/home.html`:

```html
{% extends "base.html" %}

{% block title %}My Requisitions{% endblock %}

{% block content %}
<h2>My Requisitions</h2>

<a href="{% url 'create-requisition' %}" class="btn btn-primary mb-3">Create New Requisition</a>

<table class="table table-striped">
    <thead>
        <tr>
            <th>ID</th>
            <th>Amount</th>
            <th>Purpose</th>
            <th>Status</th>
            <th>Next Approver</th>
            <th>Created</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody>
        {% for req in requisitions %}
        <tr>
            <td>{{ req.transaction_id }}</td>
            <td>${{ req.amount }}</td>
            <td>{{ req.purpose|truncatewords:10 }}</td>
            <td><span class="badge bg-info">{{ req.status }}</span></td>
            <td>
                {% if req.next_approver %}
                    {{ req.next_approver.get_display_name }}
                {% else %}
                    -
                {% endif %}
            </td>
            <td>{{ req.created_at|date:"M d, Y" }}</td>
            <td>
                <a href="{% url 'requisition-detail' req.transaction_id %}" class="btn btn-sm btn-primary">View</a>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
```

### Step 9.4: Create Requisition Detail Template

Create `templates/transactions/requisition_detail.html`:

```html
{% extends "base.html" %}

{% block title %}Requisition Details{% endblock %}

{% block content %}
<h2>Requisition Details</h2>

<table class="table">
    <tr>
        <th>Transaction ID</th>
        <td>{{ requisition.transaction_id }}</td>
    </tr>
    <tr>
        <th>Requested By</th>
        <td>{{ requisition.requested_by.get_display_name }}</td>
    </tr>
    <tr>
        <th>Amount</th>
        <td>${{ requisition.amount }}</td>
    </tr>
    <tr>
        <th>Status</th>
        <td>{{ requisition.status|title }}</td>
    </tr>
    <tr>
        <th>Next Approver</th>
        <td>
            {% if requisition.next_approver %}
                {{ requisition.next_approver.get_display_name }}
            {% else %}
                -
            {% endif %}
        </td>
    </tr>
    <tr>
        <th>Purpose</th>
        <td>{{ requisition.purpose }}</td>
    </tr>
</table>

{% if user.id == requisition.requested_by.id %}
    <div class="alert alert-warning">
        You cannot approve your own requisition — it will be routed to 
        {% if requisition.next_approver %}
            {{ requisition.next_approver.get_display_name }}
        {% else %}
            the next approver
        {% endif %}.
    </div>
{% endif %}

{% if requisition.status == 'pending_urgency_confirmation' and can_act %}
    <div class="alert alert-warning">
        <h4>⚠️ Urgent Request - Confirmation Required</h4>
        <p><strong>Urgency Reason:</strong> {{ requisition.urgency_reason }}</p>
        <form method="post" action="{% url 'confirm-urgency' requisition.transaction_id %}" class="d-inline">
            {% csrf_token %}
            <button type="submit" class="btn btn-warning">✓ Confirm Urgency & Approve</button>
        </form>
        <form method="post" action="{% url 'reject-requisition' requisition.transaction_id %}" class="d-inline">
            {% csrf_token %}
            <button type="submit" class="btn btn-danger">✗ Reject</button>
        </form>
    </div>
{% endif %}

{% if can_act and requisition.status != 'pending_urgency_confirmation' %}
    <form method="post" action="{% url 'approve-requisition' requisition.transaction_id %}" class="d-inline">
        {% csrf_token %}
        <button type="submit" class="btn btn-success">Approve</button>
    </form>
    <form method="post" action="{% url 'reject-requisition' requisition.transaction_id %}" class="d-inline">
        {% csrf_token %}
        <button type="submit" class="btn btn-danger">Reject</button>
    </form>
{% endif %}

{% if approval_trail %}
<h3 class="mt-4">Approval History</h3>
<table class="table table-sm">
    <thead>
        <tr>
            <th>Date/Time</th>
            <th>Approver</th>
            <th>Role</th>
            <th>Action</th>
            <th>Comment</th>
        </tr>
    </thead>
    <tbody>
        {% for trail in approval_trail %}
        <tr>
            <td>{{ trail.timestamp|date:"M d, Y H:i" }}</td>
            <td>
                {{ trail.user.get_display_name }}
                {% if trail.auto_escalated %}
                    <span class="badge bg-warning">⚠ Auto-escalated</span>
                {% endif %}
            </td>
            <td>{{ trail.role|title }}</td>
            <td>
                {% if trail.action == 'approved' %}
                    <span class="text-success">✓ Approved</span>
                {% elif trail.action == 'rejected' %}
                    <span class="text-danger">✗ Rejected</span>
                {% else %}
                    {{ trail.action|title }}
                {% endif %}
            </td>
            <td>{{ trail.comment }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endif %}
{% endblock %}
```

---

## 10. Admin Configuration

### Step 10.1: Enhance Django Admin

Create `accounts/admin.py`:

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User
from .views import ROLE_ACCESS

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'display_name_column', 'role_badge', 'company', 'is_active']
    list_filter = ['role', 'is_active', 'company', 'region', 'branch']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Organization', {
            'fields': ('role', 'company', 'region', 'branch', 'department', 'cost_center')
        }),
        ('Additional Info', {
            'fields': ('phone_number', 'position_title', 'is_centralized_approver')
        }),
    )
    
    def display_name_column(self, obj):
        return obj.get_display_name()
    display_name_column.short_description = 'Name'
    
    def role_badge(self, obj):
        colors = {
            'admin': 'danger',
            'cfo': 'primary',
            'treasury': 'success',
            'staff': 'secondary',
        }
        color = colors.get(obj.role, 'info')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_role_display()
        )
    role_badge.short_description = 'Role'
```

---

## 11. Management Commands

### Step 11.1: Create Superuser Script

Create `create_superuser.py`:

```python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Deprecated: DJANGO_SUPERUSER_* env vars were previously used. Use ADMIN_* env vars instead.
# For compatibility the bootstrap migrates these values at runtime, but please remove them from your environment.
username = os.environ.get('ADMIN_USERNAME', 'admin')
email = os.environ.get('ADMIN_EMAIL')
password = os.environ.get('ADMIN_PASSWORD')  # required

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
        role='admin'
    )
    print(f"✅ Superuser '{username}' created successfully!")
else:
    print(f"ℹ️ Superuser '{username}' already exists.")
```

### Step 11.2: Load Test Data Command

Create `organization/management/commands/load_comprehensive_data.py`:

```python
from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from organization.models import Company, Region, Branch, Department
from workflow.models import ApprovalThreshold
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Load comprehensive test data for all models'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Loading test data...')
        
        # Create company
        company, _ = Company.objects.get_or_create(
            code='QLS',
            defaults={'name': 'QuickServices LQS'}
        )
        
        # Create regions
        nairobi_region, _ = Region.objects.get_or_create(
            code='NBI',
            company=company,
            defaults={'name': 'Nairobi Region'}
        )
        
        # Create branches
        nairobi_branch, _ = Branch.objects.get_or_create(
            code='NBI-001',
            company=company,
            region=nairobi_region,
            defaults={'name': 'Nairobi', 'address': 'Nairobi CBD'}
        )
        
        # Create departments
        finance_dept, _ = Department.objects.get_or_create(
            code='FIN',
            company=company,
            defaults={'name': 'Finance'}
        )
        
        # Create users (10 roles)
        users_data = [
            ('admin', 'Admin', 'admin', 'admin@qls.com'),
            ('staff', 'Staff', 'nnyaga', 'staff@qls.com'),
            ('department_head', 'Department Head', 'dh', 'dh@qls.com'),
            ('branch_manager', 'Branch Manager', 'kmogare', 'bm@qls.com'),
            ('regional_manager', 'Regional Manager', 'dwanyiri', 'rm@qls.com'),
            ('group_finance_manager', 'Group Finance', 'gfm', 'gfm@qls.com'),
            ('treasury', 'Treasury', 'treasury', 'treasury@qls.com'),
            ('cfo', 'CFO', 'cfo', 'cfo@qls.com'),
            ('fp&a', 'FP&A', 'vmuindi', 'fpa@qls.com'),
            ('ceo', 'CEO', 'ceo', 'ceo@qls.com'),
        ]
        
        for role, name, username, email in users_data:
            if not User.objects.filter(username=username).exists():
                User.objects.create_user(
                    username=username,
                    email=email,
                    password='Test@123456',
                    first_name=name,
                    role=role,
                    company=company,
                    region=nairobi_region,
                    branch=nairobi_branch,
                    department=finance_dept
                )
        
        # Create approval thresholds
        thresholds_data = [
            ('Tier 1 Branch', 'BRANCH', 0, 10000, ['branch_manager', 'treasury'], True, False, 1),
            ('Tier 2 Branch', 'BRANCH', 10001, 50000, ['branch_manager', 'department_head', 'treasury'], True, False, 2),
            ('Tier 3 Branch', 'BRANCH', 50001, 250000, ['branch_manager', 'regional_manager', 'treasury', 'fp&a'], True, False, 3),
            ('Tier 4 Branch', 'BRANCH', 250001, 999999999, ['regional_manager', 'treasury', 'cfo', 'fp&a'], False, True, 4),
        ]
        
        for name, origin, min_amt, max_amt, roles, fast_track, req_cfo, priority in thresholds_data:
            ApprovalThreshold.objects.get_or_create(
                name=name,
                defaults={
                    'origin_type': origin,
                    'min_amount': Decimal(str(min_amt)),
                    'max_amount': Decimal(str(max_amt)),
                    'roles_sequence': roles,
                    'allow_urgent_fasttrack': fast_track,
                    'requires_cfo': req_cfo,
                    'priority': priority
                }
            )
        
        self.stdout.write(self.style.SUCCESS('✅ Test data loaded successfully!'))
```

---

## 12. Security & Authentication

### Step 12.1: Update Settings for Security

Add to `settings.py`:

```python
# Security settings
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Login configuration
LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/accounts/dashboard/'
LOGOUT_REDIRECT_URL = '/admin/login/'
```

---

## 13. Testing

### Step 13.1: Run Migrations

```powershell
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python create_superuser.py

# Load test data
python manage.py load_comprehensive_data
```

### Step 13.2: Test Locally

```powershell
# Run development server
python manage.py runserver

# Access application
# http://127.0.0.1:8000/
# http://127.0.0.1:8000/admin/
```

---

## 14. Deployment

### Step 14.1: Create Build Script

Create `build.sh`:

```bash
#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python create_superuser.py
python manage.py load_comprehensive_data
```

### Step 14.2: Create Procfile

Create `Procfile`:

```
web: gunicorn pettycash_system.wsgi
```

### Step 14.3: Create runtime.txt

Create `runtime.txt`:

```
python-3.13.7
```

### Step 14.4: Deploy to Render.com

1. Push code to GitHub
2. Create Render account
3. Create new Web Service
4. Connect GitHub repository
5. Set environment variables:
   - `SECRET_KEY`
   - `DATABASE_URL` (PostgreSQL)
   - `PYTHON_VERSION=3.13.7`
6. Deploy!

---

## 15. Initial Data Setup

### Step 15.1: Access Admin

1. Navigate to `https://your-app.onrender.com/admin/`
2. Login with superuser credentials
3. Verify all models are present

### Step 15.2: Configure Approval Thresholds

The test data loader creates 4 default thresholds. Customize as needed in Django admin.

### Step 15.3: Create Test Requisitions

1. Login as staff user
2. Navigate to `/transactions/`
3. Click "Create New Requisition"
4. Fill in details and submit
5. Verify workflow resolution
6. Login as approver and test approval flow

---

## 🎉 Congratulations!

You've successfully replicated the Petty Cash Management System!

### Next Steps:

1. ✅ Customize branding and styling
2. ✅ Configure email settings (SMTP)
3. ✅ Set up Celery for background tasks (optional)
4. ✅ Configure monitoring and logging
5. ✅ Run user acceptance testing
6. ✅ Deploy to production

---

**For Full Reference:**
- See `BLUEPRINT_v00.1_IMPLEMENTED.md` for detailed feature documentation
- See `ADMIN_PERMISSION_GUIDE.md` for admin usage guide
- See `SECURITY_CHECKLIST.md` for security best practices

**Support:**
- GitHub Repository: https://github.com/quickserviceslqs-netizen/pettycash_system
- Production Demo: https://pettycash-system.onrender.com

---

**Document Version:** 1.0  
**Last Updated:** November 21, 2025
