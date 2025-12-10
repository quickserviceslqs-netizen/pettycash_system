import csv
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import App, User
from organization.models import (
    Branch,
    Company,
    CostCenter,
    Department,
    Position,
    Region,
)
from settings_manager.models import ActivityLog, SystemSetting, get_setting


def is_admin_user(user):
    """Check if user is superuser or has admin role"""
    return user.is_superuser or user.role == "admin"


@login_required
@user_passes_test(is_admin_user)
def settings_dashboard(request):
    """Main settings management dashboard"""
    # Log activity
    log_activity(
        request.user,
        "view",
        content_type="Settings Dashboard",
        description="Viewed settings dashboard",
        request=request,
    )

    # Get category filter from URL if provided
    category_filter = request.GET.get("category")
    # Get text filter from URL if provided
    text_filter = request.GET.get("filter", "").strip()

    # Get all settings grouped by category - NO PAGINATION
    categories = SystemSetting.CATEGORY_CHOICES
    settings_by_category = {}
    category_counts = {}

    if category_filter:
        # Show only the filtered category
        for category_key, category_name in categories:
            if category_key == category_filter:
                all_settings = SystemSetting.objects.filter(
                    category=category_key, is_active=True
                ).order_by("display_name")
                
                # Apply text filter if provided
                if text_filter:
                    all_settings = all_settings.filter(
                        Q(display_name__icontains=text_filter) |
                        Q(key__icontains=text_filter) |
                        Q(description__icontains=text_filter)
                    )
                
                if all_settings.exists():
                    category_counts[category_key] = all_settings.count()
                    # Store with tuple (key, name, settings) for template access
                    settings_by_category[(category_key, category_name)] = all_settings
    else:
        # Show all categories
        for category_key, category_name in categories:
            all_settings = SystemSetting.objects.filter(
                category=category_key, is_active=True
            ).order_by("display_name")
            
            # Apply text filter if provided
            if text_filter:
                all_settings = all_settings.filter(
                    Q(display_name__icontains=text_filter) |
                    Q(key__icontains=text_filter) |
                    Q(description__icontains=text_filter)
                )
            
            if all_settings.exists():
                category_counts[category_key] = all_settings.count()
                # Store with tuple (key, name, settings) for template access
                settings_by_category[(category_key, category_name)] = all_settings

    # Get all active settings (for stats)
    all_settings = SystemSetting.objects.filter(is_active=True)

    context = {
        "settings_by_category": settings_by_category,
        "category_counts": category_counts,
        "all_settings": all_settings,
        "categories": categories,
        "selected_category": category_filter,
        "text_filter": text_filter,
        "total_settings": SystemSetting.objects.filter(is_active=True).count(),
    }

    return render(request, "settings_manager/dashboard.html", context)


@login_required
@user_passes_test(is_admin_user)
def edit_setting(request, setting_id):
    """Edit a system setting"""
    setting = get_object_or_404(SystemSetting, id=setting_id)

    if not setting.editable_by_admin:
        messages.error(request, "This setting cannot be edited through the UI.")
        return redirect("settings_manager:dashboard")

    if request.method == "POST":
        old_value = setting.value
        new_value = request.POST.get("value")

        setting.value = new_value
        setting.last_modified_by = request.user

        try:
            setting.full_clean()
            setting.save()

            # Log the change
            log_activity(
                request.user,
                "setting_change",
                "System Setting",
                object_id=setting.key,
                object_repr=setting.display_name,
                description=f"Changed '{setting.display_name}' from '{old_value}' to '{new_value}'",
                changes={"old_value": old_value, "new_value": new_value},
                request=request,
            )

            if setting.requires_restart:
                messages.warning(
                    request,
                    f"Setting updated successfully! NOTE: Server restart required for this change to take effect.",
                )
            else:
                messages.success(
                    request, f"Setting '{setting.display_name}' updated successfully!"
                )

        except Exception as e:
            messages.error(request, f"Error updating setting: {str(e)}")
            log_activity(
                request.user,
                "setting_change",
                "System Setting",
                object_id=setting.key,
                success=False,
                error_message=str(e),
                request=request,
            )

        return redirect("settings_manager:dashboard")

    context = {
        "setting": setting,
    }

    return render(request, "settings_manager/edit_setting.html", context)


@login_required
@user_passes_test(is_admin_user)
def activity_logs(request):
    """View activity logs with filtering"""
    # Log this view
    log_activity(
        request.user,
        "view",
        content_type="Activity Logs",
        description="Viewed activity logs",
        request=request,
    )

    # Get filters
    action_filter = request.GET.get("action")
    user_filter = request.GET.get("user")
    days_filter = int(request.GET.get("days", 7))

    # Base queryset
    logs = ActivityLog.objects.select_related("user").all()

    # Apply filters
    if action_filter:
        logs = logs.filter(action=action_filter)

    if user_filter:
        logs = logs.filter(user__username__icontains=user_filter)

    # Date filter
    if days_filter:
        start_date = timezone.now() - timedelta(days=days_filter)
        logs = logs.filter(timestamp__gte=start_date)

    # Paginate
    page_size = request.GET.get("page_size", 25)
    paginator = Paginator(logs, page_size)
    page_number = request.GET.get("page", 1)
    logs = paginator.get_page(page_number)

    # Get statistics
    stats = ActivityLog.objects.filter(
        timestamp__gte=timezone.now() - timedelta(days=days_filter)
    ).aggregate(total=Count("id"), failed=Count("id", filter=Q(success=False)))

    # Get top users
    top_users = (
        ActivityLog.objects.filter(
            timestamp__gte=timezone.now() - timedelta(days=days_filter)
        )
        .values("user__username")
        .annotate(activity_count=Count("id"))
        .order_by("-activity_count")[:5]
    )

    context = {
        "logs": logs,
        "actions": ActivityLog.ACTION_CHOICES,
        "selected_action": action_filter,
        "selected_user": user_filter,
        "days_filter": days_filter,
        "stats": stats,
        "top_users": top_users,
    }

    return render(request, "settings_manager/activity_logs.html", context)


@login_required
@user_passes_test(is_admin_user)
def system_info(request):
    """Display system information and diagnostics"""
    import platform
    import sys

    from django import get_version as django_version
    from django.conf import settings as django_settings

    # Log activity
    log_activity(
        request.user,
        "view",
        content_type="System Info",
        description="Viewed system information",
        request=request,
    )

    context = {
        "python_version": sys.version,
        "django_version": django_version(),
        "platform": platform.platform(),
        "debug_mode": django_settings.DEBUG,
        "database_engine": django_settings.DATABASES["default"]["ENGINE"],
        "installed_apps": django_settings.INSTALLED_APPS,
        "middleware": django_settings.MIDDLEWARE,
    }

    return render(request, "settings_manager/system_info.html", context)


def log_activity(
    user,
    action,
    content_type="",
    object_id="",
    object_repr="",
    description="",
    changes=None,
    success=True,
    error_message="",
    request=None,
):
    """
    Helper function to log admin activities.
    Can be called from anywhere in the application.
    Captures IP address, device name, location, and user agent.
    """
    ip_address = None
    device_name = ""
    location = ""
    user_agent = ""

    if request:
        # Get IP address
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(",")[0].strip()
        else:
            ip_address = request.META.get("REMOTE_ADDR")

        # Get location from IP address
        if ip_address and ip_address not in ["127.0.0.1", "localhost", "::1"]:
            # Check if geolocation is enabled in settings
            from settings_manager.models import get_setting

            if get_setting("ENABLE_ACTIVITY_GEOLOCATION", "true") == "true":
                try:
                    import requests

                    # Use a free IP geolocation API
                    response = requests.get(
                        f"http://ip-api.com/json/{ip_address}",
                        timeout=2,  # 2 second timeout
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("status") == "success":
                            city = data.get("city", "")
                            region = data.get("regionName", "")
                            country = data.get("country", "")

                            # Build location string
                            location_parts = []
                            if city:
                                location_parts.append(city)
                            if region and region != city:
                                location_parts.append(region)
                            if country:
                                location_parts.append(country)

                            location = ", ".join(location_parts)
                except Exception:
                    # If geolocation fails, continue without location
                    pass

        # For local development
        if not location and ip_address in ["127.0.0.1", "localhost", "::1"]:
            location = "Local Development"

        # Get device name from hostname (if available in headers)
        device_name = request.META.get("REMOTE_HOST", "")

        # If REMOTE_HOST not available, try to get from user agent
        if not device_name:
            user_agent_str = request.META.get("HTTP_USER_AGENT", "")
            # Extract device info from user agent string
            if user_agent_str:
                # Try to parse device name from user agent
                import re

                # Look for patterns like "Windows NT 10.0", "Macintosh", "Linux", etc.
                if "Windows" in user_agent_str:
                    match = re.search(r"Windows NT ([\d.]+)", user_agent_str)
                    if match:
                        version = match.group(1)
                        version_map = {
                            "10.0": "Windows 10/11",
                            "6.3": "Windows 8.1",
                            "6.2": "Windows 8",
                            "6.1": "Windows 7",
                        }
                        device_name = version_map.get(version, f"Windows NT {version}")
                elif "Macintosh" in user_agent_str or "Mac OS X" in user_agent_str:
                    match = re.search(r"Mac OS X ([\d_]+)", user_agent_str)
                    if match:
                        device_name = f"macOS {match.group(1).replace('_', '.')}"
                    else:
                        device_name = "macOS"
                elif "Linux" in user_agent_str:
                    if "Android" in user_agent_str:
                        match = re.search(r"Android ([\d.]+)", user_agent_str)
                        if match:
                            device_name = f"Android {match.group(1)}"
                        else:
                            device_name = "Android"
                    else:
                        device_name = "Linux"
                elif "iPhone" in user_agent_str or "iPad" in user_agent_str:
                    match = re.search(r"OS ([\d_]+)", user_agent_str)
                    if match:
                        device_name = f"iOS {match.group(1).replace('_', '.')}"
                    else:
                        device_name = "iOS"

                # Also try to get browser info
                if "Chrome/" in user_agent_str and "Edg/" not in user_agent_str:
                    device_name += " - Chrome" if device_name else "Chrome"
                elif "Edg/" in user_agent_str or "Edge/" in user_agent_str:
                    device_name += " - Edge" if device_name else "Edge"
                elif "Firefox/" in user_agent_str:
                    device_name += " - Firefox" if device_name else "Firefox"
                elif "Safari/" in user_agent_str and "Chrome" not in user_agent_str:
                    device_name += " - Safari" if device_name else "Safari"

        # Get user agent
        user_agent = request.META.get("HTTP_USER_AGENT", "")

    ActivityLog.objects.create(
        user=user,
        action=action,
        content_type=content_type,
        object_id=str(object_id),
        object_repr=object_repr,
        description=description,
        ip_address=ip_address,
        device_name=device_name[:255] if device_name else "",
        location=location[:255] if location else "",
        user_agent=user_agent[:500] if user_agent else "",
        changes=changes,
        success=success,
        error_message=error_message,
    )


# ==================== DATA OPERATIONS VIEWS ====================


@login_required
@user_passes_test(is_admin_user)
def data_operations_dashboard(request):
    """Main data operations dashboard"""
    # Get statistics
    stats = {
        "total_users": User.objects.count(),
        "active_users": User.objects.filter(is_active=True).count(),
        "inactive_users": User.objects.filter(is_active=False).count(),
        "total_departments": Department.objects.count(),
        "total_branches": Branch.objects.count(),
        "total_regions": Region.objects.count(),
        "total_companies": Company.objects.count(),
        "users_by_role": dict(
            User.objects.values("role").annotate(count=Count("role"))
        ),
    }

    log_activity(
        request.user,
        "view",
        "Data Operations Dashboard",
        description="Viewed data operations dashboard",
    )

    context = {"stats": stats}
    return render(request, "settings_manager/data_operations_dashboard.html", context)


@login_required
@user_passes_test(is_admin_user)
def manage_users(request):
    """User management interface"""
    search_query = request.GET.get("search", "")
    role_filter = request.GET.get("role", "")
    status_filter = request.GET.get("status", "")

    users = User.objects.all().select_related("department").order_by("-date_joined")

    if search_query:
        users = users.filter(
            Q(email__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
        )

    if role_filter:
        users = users.filter(role=role_filter)

    if status_filter == "active":
        users = users.filter(is_active=True)
    elif status_filter == "inactive":
        users = users.filter(is_active=False)

    # Paginate
    page_size = request.GET.get("page_size", 25)
    paginator = Paginator(users, page_size)
    page_number = request.GET.get("page", 1)
    users = paginator.get_page(page_number)

    context = {
        "users": users,
        "search_query": search_query,
        "role_filter": role_filter,
        "status_filter": status_filter,
        "roles": User.ROLE_CHOICES,
    }

    return render(request, "settings_manager/manage_users.html", context)


@login_required
@user_passes_test(is_admin_user)
def create_user(request):
    """Create new user"""
    if request.method == "POST":
        try:
            email = request.POST.get("email")
            first_name = request.POST.get("first_name")
            last_name = request.POST.get("last_name")
            role = request.POST.get("role")
            department_id = request.POST.get("department")
            password = request.POST.get("password")

            # Check if user exists
            if User.objects.filter(email=email).exists():
                messages.error(request, f"User with email {email} already exists.")
                return redirect("settings_manager:create_user")

            # Create user
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role,
            )

            if department_id:
                user.department_id = department_id
                user.save()

            log_activity(
                request.user,
                "create",
                content_type="User",
                object_id=user.id,
                object_repr=str(user),
                description=f"Created user: {user.email}",
                changes={
                    "email": user.email,
                    "role": user.role,
                    "department": str(user.department) if user.department else None,
                },
                request=request,
            )
            messages.success(request, f"User {user.email} created successfully.")
            return redirect("settings_manager:manage_users")

        except Exception as e:
            messages.error(request, f"Error creating user: {str(e)}")
            log_activity(
                request.user,
                "create",
                content_type="User",
                description=f"Failed to create user",
                success=False,
                error_message=str(e),
                request=request,
            )

    context = {
        "departments": Department.objects.all().select_related("branch"),
        "roles": User.ROLE_CHOICES,
    }
    return render(request, "settings_manager/create_user.html", context)


@login_required
@user_passes_test(is_admin_user)
def edit_user(request, user_id):
    """Edit existing user"""
    user_obj = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        try:
            user_obj.first_name = request.POST.get("first_name")
            user_obj.last_name = request.POST.get("last_name")
            user_obj.role = request.POST.get("role")
            user_obj.is_active = request.POST.get("is_active") == "on"

            department_id = request.POST.get("department")
            if department_id:
                user_obj.department_id = department_id

            user_obj.save()

            old_values = {
                k: request.POST.get(f"old_{k}", "")
                for k in ["email", "first_name", "last_name", "role"]
            }
            new_values = {
                "email": user_obj.email,
                "first_name": user_obj.first_name,
                "last_name": user_obj.last_name,
                "role": user_obj.role,
            }

            log_activity(
                request.user,
                "update",
                content_type="User",
                object_id=user_obj.id,
                object_repr=str(user_obj),
                description=f"Updated user: {user_obj.email}",
                changes={"before": old_values, "after": new_values},
                request=request,
            )
            messages.success(request, f"User {user_obj.email} updated successfully.")
            return redirect("settings_manager:manage_users")

        except Exception as e:
            messages.error(request, f"Error updating user: {str(e)}")
            log_activity(
                request.user,
                "update",
                content_type="User",
                object_id=user_obj.id,
                description=f"Failed to update user {user_obj.email}",
                success=False,
                error_message=str(e),
                request=request,
            )

    context = {
        "user_obj": user_obj,
        "departments": Department.objects.all().select_related("branch"),
        "roles": User.ROLE_CHOICES,
    }
    return render(request, "settings_manager/edit_user.html", context)


@login_required
@user_passes_test(is_admin_user)
def toggle_user_status(request, user_id):
    """Activate/Deactivate user"""
    user_obj = get_object_or_404(User, id=user_id)
    user_obj.is_active = not user_obj.is_active
    user_obj.save()

    status = "activated" if user_obj.is_active else "deactivated"
    log_activity(
        request.user,
        "update",
        content_type="User",
        object_id=user_obj.id,
        object_repr=str(user_obj),
        description=f"{status.capitalize()} user: {user_obj.email}",
        changes={"is_active": user_obj.is_active, "status": status},
        request=request,
    )
    messages.success(request, f"User {user_obj.email} {status} successfully.")

    return redirect("settings_manager:manage_users")


@login_required
@user_passes_test(is_admin_user)
def manage_departments(request):
    """Department management interface"""
    search_query = request.GET.get("search", "")
    branch_filter = request.GET.get("branch", "")

    departments = (
        Department.objects.all()
        .select_related("branch", "branch__region")
        .order_by("name")
    )

    if search_query:
        departments = departments.filter(name__icontains=search_query)

    if branch_filter:
        departments = departments.filter(branch_id=branch_filter)

    # Paginate
    page_size = request.GET.get("page_size", 25)
    paginator = Paginator(departments, page_size)
    page_number = request.GET.get("page", 1)
    departments = paginator.get_page(page_number)

    context = {
        "departments": departments,
        "branches": Branch.objects.all().select_related("region"),
        "search_query": search_query,
        "branch_filter": branch_filter,
    }

    return render(request, "settings_manager/manage_departments.html", context)


@login_required
@user_passes_test(is_admin_user)
def create_department(request):
    """Create new department"""
    if request.method == "POST":
        try:
            name = request.POST.get("name")
            branch_id = request.POST.get("branch")

            department = Department.objects.create(name=name, branch_id=branch_id)

            log_activity(
                request.user,
                "create",
                content_type="Department",
                object_id=department.id,
                object_repr=str(department),
                description=f"Created department: {department.name}",
                changes={"name": department.name, "branch": str(department.branch)},
                request=request,
            )
            messages.success(
                request, f"Department {department.name} created successfully."
            )
            return redirect("settings_manager:manage_departments")

        except Exception as e:
            messages.error(request, f"Error creating department: {str(e)}")
            log_activity(
                request.user,
                "create",
                content_type="Department",
                description=f"Failed to create department",
                success=False,
                error_message=str(e),
                request=request,
            )

    context = {
        "branches": Branch.objects.all().select_related("region"),
    }
    return render(request, "settings_manager/create_department.html", context)


@login_required
@user_passes_test(is_admin_user)
def edit_department(request, department_id):
    """Edit existing department"""
    department = get_object_or_404(Department, id=department_id)

    if request.method == "POST":
        try:
            old_name = department.name
            old_branch = department.branch

            department.name = request.POST.get("name")
            branch_id = request.POST.get("branch")
            if branch_id:
                department.branch_id = branch_id

            department.save()

            log_activity(
                request.user,
                "update",
                content_type="Department",
                object_id=department.id,
                object_repr=str(department),
                description=f"Updated department: {department.name}",
                changes={
                    "old_name": old_name,
                    "new_name": department.name,
                    "old_branch": str(old_branch),
                    "new_branch": str(department.branch),
                },
                request=request,
            )
            messages.success(
                request, f"Department {department.name} updated successfully."
            )
            return redirect("settings_manager:manage_departments")

        except Exception as e:
            messages.error(request, f"Error updating department: {str(e)}")
            log_activity(
                request.user,
                "update",
                content_type="Department",
                object_id=department.id,
                description=f"Failed to update department",
                success=False,
                error_message=str(e),
                request=request,
            )

    context = {
        "department": department,
        "branches": Branch.objects.all().select_related("region"),
    }
    return render(request, "settings_manager/edit_department.html", context)


@login_required
@user_passes_test(is_admin_user)
def delete_department(request, department_id):
    """Delete department"""
    department = get_object_or_404(Department, id=department_id)

    if request.method == "POST":
        name = department.name
        department.delete()

        log_activity(
            request.user,
            "delete",
            content_type="Department",
            description=f"Deleted department: {name}",
            request=request,
        )
        messages.success(request, f"Department {name} deleted successfully.")

    return redirect("settings_manager:manage_departments")


@login_required
@user_passes_test(is_admin_user)
def manage_regions(request):
    """Region management interface"""
    regions = Region.objects.all().select_related("company").order_by("name")

    # Paginate
    page_size = request.GET.get("page_size", 25)
    paginator = Paginator(regions, page_size)
    page_number = request.GET.get("page", 1)
    regions = paginator.get_page(page_number)

    context = {
        "regions": regions,
        "companies": Company.objects.all(),
    }

    return render(request, "settings_manager/manage_regions.html", context)


@login_required
@user_passes_test(is_admin_user)
def create_region(request):
    """Create new region"""
    if request.method == "POST":
        try:
            name = request.POST.get("name")
            code = request.POST.get("code")
            company_id = request.POST.get("company")

            region = Region.objects.create(name=name, code=code, company_id=company_id)

            log_activity(
                request.user,
                "create",
                content_type="Region",
                object_id=region.id,
                object_repr=str(region),
                description=f"Created region: {region.name}",
                changes={
                    "name": region.name,
                    "code": region.code,
                    "company": str(region.company),
                },
                request=request,
            )
            messages.success(request, f"Region {region.name} created successfully.")
            return redirect("settings_manager:manage_regions")

        except Exception as e:
            messages.error(request, f"Error creating region: {str(e)}")
            log_activity(
                request.user,
                "create",
                content_type="Region",
                description=f"Failed to create region",
                success=False,
                error_message=str(e),
                request=request,
            )

    context = {
        "companies": Company.objects.all(),
    }
    return render(request, "settings_manager/create_region.html", context)


@login_required
@user_passes_test(is_admin_user)
def edit_region(request, region_id):
    """Edit existing region"""
    region = get_object_or_404(Region, id=region_id)

    if request.method == "POST":
        try:
            old_name = region.name
            old_code = region.code
            old_company = region.company

            region.name = request.POST.get("name")
            region.code = request.POST.get("code")
            company_id = request.POST.get("company")
            if company_id:
                region.company_id = company_id

            region.save()

            log_activity(
                request.user,
                "update",
                content_type="Region",
                object_id=region.id,
                object_repr=str(region),
                description=f"Updated region: {region.name}",
                changes={
                    "old_name": old_name,
                    "new_name": region.name,
                    "old_code": old_code,
                    "new_code": region.code,
                    "old_company": str(old_company),
                    "new_company": str(region.company),
                },
                request=request,
            )
            messages.success(request, f"Region {region.name} updated successfully.")
            return redirect("settings_manager:manage_regions")

        except Exception as e:
            messages.error(request, f"Error updating region: {str(e)}")
            log_activity(
                request.user,
                "update",
                content_type="Region",
                object_id=region.id,
                description=f"Failed to update region",
                success=False,
                error_message=str(e),
                request=request,
            )

    context = {
        "region": region,
        "companies": Company.objects.all(),
    }
    return render(request, "settings_manager/edit_region.html", context)


@login_required
@user_passes_test(is_admin_user)
def delete_region(request, region_id):
    """Delete region"""
    region = get_object_or_404(Region, id=region_id)

    if request.method == "POST":
        name = region.name
        region.delete()

        log_activity(
            request.user,
            "delete",
            content_type="Region",
            description=f"Deleted region: {name}",
            request=request,
        )
        messages.success(request, f"Region {name} deleted successfully.")

    return redirect("settings_manager:manage_regions")


@login_required
@user_passes_test(is_admin_user)
def export_users_csv(request):
    """Export users to CSV"""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="users_export.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "Email",
            "First Name",
            "Last Name",
            "Role",
            "Department",
            "Branch",
            "Active",
            "Date Joined",
        ]
    )

    users = User.objects.all().select_related("department", "department__branch")
    for user in users:
        writer.writerow(
            [
                user.email,
                user.first_name,
                user.last_name,
                user.get_role_display(),
                user.department.name if user.department else "",
                (
                    user.department.branch.name
                    if user.department and user.department.branch
                    else ""
                ),
                "Yes" if user.is_active else "No",
                user.date_joined.strftime("%Y-%m-%d"),
            ]
        )

    log_activity(
        request.user,
        "export",
        content_type="User Data",
        description=f"Exported {users.count()} users to CSV",
        changes={"count": users.count(), "format": "CSV"},
        request=request,
    )
    return response
