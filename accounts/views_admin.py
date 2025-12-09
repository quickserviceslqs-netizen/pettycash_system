"""
Admin Dashboard Views
User-friendly interface for managing users, permissions, and app access
Admin stats are integrated into the main dashboard (accounts/views.py)
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse
from django.http import HttpResponse
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.utils.crypto import get_random_string
from accounts.models import User, App, UserAuditLog
from organization.models import Company, Branch, Department
from django.contrib.sessions.models import Session
from django.utils import timezone


@login_required
@permission_required("accounts.change_user", raise_exception=True)
def manage_users(request):
    """User management page with search and filters"""

    # Get filter parameters
    role_filter = request.GET.get("role", "")
    company_filter = request.GET.get("company", "")
    status_filter = request.GET.get("status", "")
    search = request.GET.get("search", "")

    # Base queryset
    users = User.objects.select_related(
        "company", "branch", "department"
    ).prefetch_related("assigned_apps")

    # Apply filters
    if role_filter:
        users = users.filter(role=role_filter)
    if company_filter:
        users = users.filter(company_id=company_filter)
    if status_filter == "active":
        users = users.filter(is_active=True)
    elif status_filter == "inactive":
        users = users.filter(is_active=False)
    elif status_filter == "locked":
        users = users.filter(
            lockout_until__isnull=False, lockout_until__gt=timezone.now()
        )
    if search:
        users = users.filter(
            Q(username__icontains=search)
            | Q(email__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
        )

    # Order by username
    users = users.order_by("username")

    # Pagination
    from django.core.paginator import Paginator

    try:
        page_size = int(request.GET.get("page_size", 10))
    except (TypeError, ValueError):
        page_size = 10
    page_size = max(5, min(page_size, 200))  # sane bounds
    page_number = request.GET.get("page", 1)
    paginator = Paginator(users, page_size)
    page_obj = paginator.get_page(page_number)

    # Get filter options
    companies = Company.objects.all().order_by("name")
    roles = User.ROLE_CHOICES
    all_apps = App.objects.filter(is_active=True).order_by("display_name", "name")

    context = {
        "users": page_obj,
        "companies": companies,
        "roles": roles,
        "all_apps": all_apps,
        "role_filter": role_filter,
        "company_filter": company_filter,
        "status_filter": status_filter,
        "search": search,
        "page_obj": page_obj,
        "page_size": page_size,
    }

    return render(request, "accounts/manage_users.html", context)


@login_required
@permission_required("accounts.view_user", raise_exception=True)
def export_users(request):
    """Export filtered users to CSV using same filters as manage_users"""
    import csv

    role_filter = request.GET.get("role", "")
    company_filter = request.GET.get("company", "")
    status_filter = request.GET.get("status", "")
    search = request.GET.get("search", "")
    cols_param = request.GET.get("cols", "")
    selected_cols = [c.strip() for c in cols_param.split(",") if c.strip()]

    users = User.objects.select_related("company", "branch", "department").all()

    if role_filter:
        users = users.filter(role=role_filter)
    if company_filter:
        users = users.filter(company_id=company_filter)
    if status_filter == "active":
        users = users.filter(is_active=True)
    elif status_filter == "inactive":
        users = users.filter(is_active=False)
    if search:
        users = users.filter(
            Q(username__icontains=search)
            | Q(email__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
        )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="users_export.csv"'

    writer = csv.writer(response)
    # Base headers
    headers = ["Username", "Name", "Email", "Role", "Company", "Branch", "Department"]

    # Optional columns map
    optional_map = {
        "cost-center": (
            "Cost Center",
            lambda u: getattr(getattr(u, "cost_center", None), "name", "") or "",
        ),
        "position": (
            "Position",
            lambda u: getattr(getattr(u, "position_title", None), "name", "") or "",
        ),
        "region": (
            "Region",
            lambda u: getattr(getattr(u, "region", None), "name", "") or "",
        ),
        "phone": ("Phone", lambda u: u.phone_number or ""),
    }

    for key in selected_cols:
        if key in optional_map:
            headers.append(optional_map[key][0])

    headers.append("Active")
    writer.writerow(headers)
    for u in users.order_by("username"):
        base = [
            u.username,
            u.get_display_name(),
            u.email or "",
            u.get_role_display(),
            u.company.name if u.company else "",
            u.branch.name if u.branch else "",
            u.department.name if u.department else "",
        ]
        # Append optional values in the requested order
        for key in selected_cols:
            if key in optional_map:
                base.append(optional_map[key][1](u))
        base.append("Yes" if u.is_active else "No")
        writer.writerow(base)

    return response


@login_required
@permission_required("accounts.view_user", raise_exception=True)
def audit_logs(request):
    """View user audit logs with filtering"""
    logs = UserAuditLog.objects.select_related("target_user", "performed_by").all()

    # Filters
    target_user_id = request.GET.get("target_user")
    performed_by_id = request.GET.get("performed_by")
    action_filter = request.GET.get("action")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    if target_user_id:
        logs = logs.filter(target_user_id=target_user_id)
    if performed_by_id:
        logs = logs.filter(performed_by_id=performed_by_id)
    if action_filter:
        logs = logs.filter(action=action_filter)
    if date_from:
        logs = logs.filter(timestamp__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__lte=date_to)

    # Pagination
    from django.core.paginator import Paginator

    paginator = Paginator(logs, 50)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Get filter options
    all_users = User.objects.all().order_by("username")

    context = {
        "page_obj": page_obj,
        "all_users": all_users,
        "action_choices": UserAuditLog.ACTION_CHOICES,
        "filters": {
            "target_user": target_user_id,
            "performed_by": performed_by_id,
            "action": action_filter,
            "date_from": date_from,
            "date_to": date_to,
        },
    }
    return render(request, "accounts/audit_logs.html", context)


@login_required
@permission_required("accounts.view_user", raise_exception=True)
def export_audit_logs(request):
    """Export user audit logs to CSV using same filters as audit_logs."""
    import csv

    logs = UserAuditLog.objects.select_related("target_user", "performed_by").all()

    target_user_id = request.GET.get("target_user")
    performed_by_id = request.GET.get("performed_by")
    action_filter = request.GET.get("action")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    if target_user_id:
        logs = logs.filter(target_user_id=target_user_id)
    if performed_by_id:
        logs = logs.filter(performed_by_id=performed_by_id)
    if action_filter:
        logs = logs.filter(action=action_filter)
    if date_from:
        logs = logs.filter(timestamp__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__lte=date_to)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="user_audit_logs.csv"'
    writer = csv.writer(response)
    writer.writerow(
        ["Timestamp", "Action", "Target User", "Performed By", "IP", "Notes", "Changes"]
    )
    for l in logs.order_by("-timestamp"):
        writer.writerow(
            [
                l.timestamp.isoformat(),
                l.get_action_display(),
                getattr(l.target_user, "username", ""),
                getattr(l.performed_by, "username", "") if l.performed_by else "System",
                l.ip_address or "",
                (l.notes or "").replace("\n", " ").strip(),
                l.changes,
            ]
        )

    return response


@login_required
@permission_required("accounts.view_user", raise_exception=True)
def user_sessions(request, user_id):
    """List active sessions for a user and allow termination."""
    target = get_object_or_404(User, id=user_id)
    sessions = []
    for s in Session.objects.all():
        try:
            data = s.get_decoded()
        except Exception:
            continue
        uid = str(data.get("_auth_user_id")) if data else None
        if uid and int(uid) == target.id:
            sessions.append(
                {
                    "key": s.session_key,
                    "expire_date": s.expire_date,
                    "ip": data.get("ip"),
                    "ua": (data.get("ua") or "")[:80],
                    "login_time": data.get("login_time"),
                }
            )
    sessions = sorted(sessions, key=lambda x: x["expire_date"])
    return render(
        request,
        "accounts/user_sessions.html",
        {
            "target_user": target,
            "sessions": sessions,
        },
    )


@login_required
@permission_required("accounts.change_user", raise_exception=True)
def terminate_session(request, user_id):
    if request.method == "POST":
        key = request.POST.get("session_key")
        if key:
            Session.objects.filter(session_key=key).delete()
            messages.success(request, "Session terminated.")
    return redirect("accounts:user_sessions", user_id=user_id)


@login_required
@permission_required("accounts.change_user", raise_exception=True)
def terminate_all_sessions(request, user_id):
    if request.method == "POST":
        target = get_object_or_404(User, id=user_id)
        deleted = 0
        for s in Session.objects.all():
            try:
                data = s.get_decoded()
            except Exception:
                continue
            uid = str(data.get("_auth_user_id")) if data else None
            if uid and int(uid) == target.id:
                s.delete()
                deleted += 1
        if deleted:
            messages.success(request, f"Terminated {deleted} session(s).")
        else:
            messages.info(request, "No active sessions to terminate.")
    return redirect("accounts:user_sessions", user_id=user_id)


@login_required
@permission_required("accounts.change_user", raise_exception=True)
def unlock_user(request, user_id):
    if request.method == "POST":
        target = get_object_or_404(User, id=user_id)
        target.failed_login_attempts = 0
        target.lockout_until = None
        target.save(update_fields=["failed_login_attempts", "lockout_until"])
        messages.success(request, f"User {target.username} has been unlocked.")
    return redirect("accounts:edit_user_permissions", user_id=user_id)


@login_required
@permission_required("accounts.add_user", raise_exception=True)
def create_user(request):
    """Create a new user with details, apps, groups, and permissions"""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        role = request.POST.get("role")
        is_active = request.POST.get("is_active") == "on"

        company_id = request.POST.get("company") or None
        branch_id = request.POST.get("branch") or None
        department_id = request.POST.get("department") or None

        if not username:
            messages.error(request, "Username is required.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        elif email and User.objects.filter(email=email).exists():
            messages.error(request, f"Email {email} is already in use.")
        else:
            # Role-specific validation
            validation_error = None
            if role == "branch_manager" and not branch_id:
                validation_error = "Branch Manager role requires a branch assignment."
            elif role == "regional_manager" and not company_id:
                validation_error = (
                    "Regional Manager role requires a company assignment."
                )
            elif role == "department_head" and not department_id:
                validation_error = (
                    "Department Head role requires a department assignment."
                )

            if validation_error:
                messages.error(request, validation_error)
            else:
                temp_password = get_random_string(12)
            user = User.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=role if role in dict(User.ROLE_CHOICES) else User.REQUESTER,
                is_active=is_active,
                company_id=company_id,
                branch_id=branch_id,
                department_id=department_id,
            )
            user.set_password(temp_password)
            user.save()

            # Apps
            app_ids = request.POST.getlist("apps")
            if app_ids:
                apps = App.objects.filter(id__in=app_ids, is_active=True)
                user.assigned_apps.set(apps)

            # Groups
            group_ids = request.POST.getlist("groups")
            if group_ids:
                groups = Group.objects.filter(id__in=group_ids)
                user.groups.set(groups)

            # Permissions
            permission_ids = request.POST.getlist("permissions")
            if permission_ids:
                perms = Permission.objects.filter(id__in=permission_ids)
                user.user_permissions.set(perms)

            # Audit log
            UserAuditLog.objects.create(
                target_user=user,
                performed_by=request.user,
                action="create",
                changes={
                    "username": username,
                    "role": role,
                    "email": email,
                    "is_active": is_active,
                },
                ip_address=request.META.get("REMOTE_ADDR"),
            )

            messages.success(
                request, f"User {username} created. Temporary password: {temp_password}"
            )
            return redirect("accounts:manage_users")

    # GET: show form
    companies = Company.objects.all().order_by("name")
    branches = Branch.objects.all().order_by("name")
    departments = Department.objects.all().order_by("name")
    all_apps = App.objects.filter(is_active=True)
    all_groups = Group.objects.all().order_by("name")

    content_types = ContentType.objects.filter(
        app_label__in=[
            "transactions",
            "workflow",
            "treasury",
            "reports",
            "accounts",
            "organization",
            "settings_manager",
        ]
    ).order_by("app_label", "model")

    permissions_by_app = {}
    for ct in content_types:
        app_label = ct.app_label
        permissions_by_app.setdefault(app_label, [])
        perms = Permission.objects.filter(content_type=ct).order_by("codename")
        for perm in perms:
            permissions_by_app[app_label].append(
                {
                    "id": perm.id,
                    "name": perm.name,
                    "codename": perm.codename,
                    "model": ct.model,
                }
            )

    context = {
        "companies": companies,
        "branches": branches,
        "departments": departments,
        "roles": User.ROLE_CHOICES,
        "all_apps": all_apps,
        "all_groups": all_groups,
        "permissions_by_app": permissions_by_app,
    }
    return render(request, "accounts/create_user.html", context)


@login_required
@permission_required("accounts.change_user", raise_exception=True)
def edit_user_permissions(request, user_id):
    """Edit user's app access and role"""

    user_to_edit = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        # Update role
        new_role = request.POST.get("role")
        if new_role in dict(User.ROLE_CHOICES):
            user_to_edit.role = new_role

        # Validate email uniqueness
        new_email = request.POST.get("email", user_to_edit.email)
        if (
            new_email
            and User.objects.filter(email=new_email)
            .exclude(id=user_to_edit.id)
            .exists()
        ):
            messages.error(
                request, f"Email {new_email} is already in use by another user."
            )
            return redirect("accounts:edit_user_permissions", user_id=user_id)

        # Update basic details
        user_to_edit.first_name = request.POST.get(
            "first_name", user_to_edit.first_name
        )
        user_to_edit.last_name = request.POST.get("last_name", user_to_edit.last_name)
        user_to_edit.email = new_email

        # Update app access
        app_ids = request.POST.getlist("apps")
        apps = App.objects.filter(id__in=app_ids, is_active=True)
        user_to_edit.assigned_apps.set(apps)

        # Update organization
        company_id = request.POST.get("company")
        branch_id = request.POST.get("branch")
        department_id = request.POST.get("department")

        user_to_edit.company_id = company_id or None
        user_to_edit.branch_id = branch_id or None
        user_to_edit.department_id = department_id or None

        # Update centralized approver
        user_to_edit.is_centralized_approver = (
            request.POST.get("is_centralized_approver") == "on"
        )

        # Update active status
        user_to_edit.is_active = request.POST.get("is_active") == "on"

        # Update Django permissions
        permission_ids = request.POST.getlist("permissions")
        permissions = Permission.objects.filter(id__in=permission_ids)
        user_to_edit.user_permissions.set(permissions)

        # Update groups
        group_ids = request.POST.getlist("groups")
        groups = Group.objects.filter(id__in=group_ids)
        user_to_edit.groups.set(groups)

        user_to_edit.save()

        # Audit log
        UserAuditLog.objects.create(
            target_user=user_to_edit,
            performed_by=request.user,
            action="update",
            changes={
                "role": new_role,
                "apps": list(apps.values_list("name", flat=True)),
                "groups": list(groups.values_list("name", flat=True)),
            },
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        messages.success(request, f"User {user_to_edit.username} updated successfully!")
        return redirect("accounts:manage_users")

    # GET request - show form
    all_apps = App.objects.filter(is_active=True)
    user_apps = user_to_edit.assigned_apps.all()
    companies = Company.objects.all().order_by("name")
    branches = Branch.objects.all().order_by("name")
    departments = Department.objects.all().order_by("name")

    # Get relevant permissions grouped by app/model
    content_types = ContentType.objects.filter(
        app_label__in=[
            "transactions",
            "workflow",
            "treasury",
            "reports",
            "accounts",
            "organization",
            "settings_manager",
        ]
    ).order_by("app_label", "model")

    permissions_by_app = {}
    for ct in content_types:
        app_label = ct.app_label
        if app_label not in permissions_by_app:
            permissions_by_app[app_label] = []

        perms = Permission.objects.filter(content_type=ct).order_by("codename")
        for perm in perms:
            permissions_by_app[app_label].append(
                {
                    "id": perm.id,
                    "name": perm.name,
                    "codename": perm.codename,
                    "model": ct.model,
                }
            )

    user_permission_ids = list(
        user_to_edit.user_permissions.values_list("id", flat=True)
    )

    # Get all groups
    all_groups = Group.objects.all().order_by("name")
    user_group_ids = list(user_to_edit.groups.values_list("id", flat=True))

    context = {
        "user_to_edit": user_to_edit,
        "all_apps": all_apps,
        "user_apps": user_apps,
        "companies": companies,
        "branches": branches,
        "departments": departments,
        "roles": User.ROLE_CHOICES,
        "permissions_by_app": permissions_by_app,
        "user_permission_ids": user_permission_ids,
        "all_groups": all_groups,
        "user_group_ids": user_group_ids,
    }

    return render(request, "accounts/edit_user_permissions.html", context)


@login_required
@permission_required("accounts.change_user", raise_exception=True)
def toggle_user_status(request, user_id):
    """Quick toggle for user active status"""

    if request.method == "POST":
        user = get_object_or_404(User, id=user_id)
        was_active = user.is_active
        user.is_active = not user.is_active
        user.save()

        status = "activated" if user.is_active else "deactivated"

        # Audit log
        UserAuditLog.objects.create(
            target_user=user,
            performed_by=request.user,
            action="activate" if user.is_active else "deactivate",
            changes={"is_active": {"from": was_active, "to": user.is_active}},
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        messages.success(request, f"User {user.username} {status} successfully!")

    return redirect("accounts:manage_users")


@login_required
@permission_required("accounts.change_user", raise_exception=True)
def reset_user_password(request, user_id):
    """Send password reset email to user"""
    if request.method == "POST":
        user = get_object_or_404(User, id=user_id)

        if not user.email:
            messages.error(
                request, f"User {user.username} has no email address configured."
            )
        else:
            from django.contrib.auth.forms import PasswordResetForm

            form = PasswordResetForm({"email": user.email})
            if form.is_valid():
                form.save(
                    request=request,
                    use_https=request.is_secure(),
                    email_template_name="registration/password_reset_email.html",
                )

                # Audit log
                UserAuditLog.objects.create(
                    target_user=user,
                    performed_by=request.user,
                    action="password_reset",
                    notes=f"Password reset email sent to {user.email}",
                    ip_address=request.META.get("REMOTE_ADDR"),
                )

                messages.success(request, f"Password reset email sent to {user.email}")
            else:
                messages.error(request, "Failed to send password reset email.")

    return redirect("accounts:manage_users")


@login_required
@permission_required("accounts.change_user", raise_exception=True)
def bulk_assign_app(request):
    """Bulk assign app to multiple users"""

    if request.method == "POST":
        user_ids = request.POST.getlist("user_ids")
        app_id = request.POST.get("app_id")

        if user_ids and app_id:
            app = get_object_or_404(App, id=app_id)
            users = User.objects.filter(id__in=user_ids)

            for user in users:
                user.assigned_apps.add(app)

            messages.success(
                request,
                f'App "{app.display_name}" assigned to {users.count()} user(s)!',
            )
        else:
            messages.error(request, "Please select users and an app.")

    return redirect("accounts:manage_users")


@login_required
@permission_required("accounts.delete_user", raise_exception=True)
def delete_user(request, user_id):
    """Delete a user account (soft delete recommended)"""

    if request.method == "POST":
        user = get_object_or_404(User, id=user_id)

        # Prevent deleting yourself
        if user.id == request.user.id:
            messages.error(request, "You cannot delete your own account.")
            return redirect("accounts:manage_users")

        # Prevent deleting superusers (optional safety check)
        if user.is_superuser and not request.user.is_superuser:
            messages.error(request, "Only superusers can delete other superusers.")
            return redirect("accounts:manage_users")

        username = user.username
        user_data = {
            "username": user.username,
            "email": user.email,
            "role": user.get_role_display(),
            "company": str(user.company) if user.company else None,
        }

        # Audit log before deletion
        UserAuditLog.objects.create(
            target_user=user,
            performed_by=request.user,
            action="delete",
            changes=user_data,
            notes=f"User {username} deleted",
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        # Delete the user
        user.delete()

        messages.success(request, f'User "{username}" has been deleted successfully.')

    return redirect("accounts:manage_users")


@login_required
@permission_required("accounts.change_user", raise_exception=True)
def bulk_update_status(request):
    """Bulk activate or deactivate users based on `status` query param (activate|deactivate)"""
    if request.method != "POST":
        return redirect("accounts:manage_users")

    status = request.GET.get("status")
    user_ids = request.POST.getlist("user_ids")

    if not user_ids:
        messages.error(request, "Please select at least one user.")
        return redirect("accounts:manage_users")

    if status not in ("activate", "deactivate"):
        messages.error(request, "Invalid status action requested.")
        return redirect("accounts:manage_users")

    desired_state = True if status == "activate" else False
    users = User.objects.filter(id__in=user_ids)

    count = 0
    for user in users:
        if user.is_active != desired_state:
            was_active = user.is_active
            user.is_active = desired_state
            user.save(update_fields=["is_active"])
            count += 1

            UserAuditLog.objects.create(
                target_user=user,
                performed_by=request.user,
                action="activate" if desired_state else "deactivate",
                changes={"is_active": {"from": was_active, "to": desired_state}},
                ip_address=request.META.get("REMOTE_ADDR"),
            )

    if count:
        messages.success(
            request,
            f'{"Activated" if desired_state else "Deactivated"} {count} user(s).',
        )
    else:
        messages.info(request, "No changes were necessary.")

    return redirect("accounts:manage_users")


# ==========================================
# Permission Groups Management
# ==========================================


@login_required
@permission_required("auth.view_group", raise_exception=True)
def manage_groups(request):
    """View and manage permission groups"""
    groups = Group.objects.annotate(
        num_users=Count("user"), num_permissions=Count("permissions")
    ).order_by("name")

    context = {
        "groups": groups,
    }

    return render(request, "accounts/manage_groups.html", context)


@login_required
@permission_required("auth.add_group", raise_exception=True)
def create_group(request):
    """Create a new permission group"""
    if request.method == "POST":
        group_name = request.POST.get("name")
        permission_ids = request.POST.getlist("permissions")

        if group_name:
            group = Group.objects.create(name=group_name)

            if permission_ids:
                permissions = Permission.objects.filter(id__in=permission_ids)
                group.permissions.set(permissions)

            messages.success(request, f'Group "{group_name}" created successfully!')
            return redirect("accounts:manage_groups")
        else:
            messages.error(request, "Group name is required.")

    # GET request - show form
    content_types = ContentType.objects.filter(
        app_label__in=[
            "transactions",
            "workflow",
            "treasury",
            "reports",
            "accounts",
            "organization",
            "settings_manager",
        ]
    ).order_by("app_label", "model")

    permissions_by_app = {}
    for ct in content_types:
        app_label = ct.app_label
        if app_label not in permissions_by_app:
            permissions_by_app[app_label] = []

        perms = Permission.objects.filter(content_type=ct).order_by("codename")
        for perm in perms:
            permissions_by_app[app_label].append(
                {
                    "id": perm.id,
                    "name": perm.name,
                    "codename": perm.codename,
                    "model": ct.model,
                }
            )

    context = {
        "permissions_by_app": permissions_by_app,
    }

    return render(request, "accounts/create_group.html", context)


@login_required
@permission_required("auth.change_group", raise_exception=True)
def edit_group(request, group_id):
    """Edit an existing permission group"""
    group = get_object_or_404(Group, id=group_id)

    if request.method == "POST":
        group_name = request.POST.get("name")
        permission_ids = request.POST.getlist("permissions")

        if group_name:
            group.name = group_name
            group.save()

            permissions = Permission.objects.filter(id__in=permission_ids)
            group.permissions.set(permissions)

            messages.success(request, f'Group "{group_name}" updated successfully!')
            return redirect("accounts:manage_groups")
        else:
            messages.error(request, "Group name is required.")

    # GET request - show form
    content_types = ContentType.objects.filter(
        app_label__in=[
            "transactions",
            "workflow",
            "treasury",
            "reports",
            "accounts",
            "organization",
            "settings_manager",
        ]
    ).order_by("app_label", "model")

    permissions_by_app = {}
    for ct in content_types:
        app_label = ct.app_label
        if app_label not in permissions_by_app:
            permissions_by_app[app_label] = []

        perms = Permission.objects.filter(content_type=ct).order_by("codename")
        for perm in perms:
            permissions_by_app[app_label].append(
                {
                    "id": perm.id,
                    "name": perm.name,
                    "codename": perm.codename,
                    "model": ct.model,
                }
            )

    group_permission_ids = list(group.permissions.values_list("id", flat=True))

    context = {
        "group": group,
        "permissions_by_app": permissions_by_app,
        "group_permission_ids": group_permission_ids,
    }

    return render(request, "accounts/edit_group.html", context)


@login_required
@permission_required("auth.delete_group", raise_exception=True)
def delete_group(request, group_id):
    """Delete a permission group"""
    group = get_object_or_404(Group, id=group_id)

    if request.method == "POST":
        group_name = group.name
        group.delete()
        messages.success(request, f'Group "{group_name}" deleted successfully!')

    return redirect("accounts:manage_groups")
