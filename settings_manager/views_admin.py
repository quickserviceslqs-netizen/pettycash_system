"""
Admin views for Activity Log management.
Provides comprehensive audit trail viewing, filtering, and export functionality.
"""

import csv
import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from accounts.models import User
from settings_manager.models import ActivityLog


def is_admin_user(user):
    """Check if user is superuser or has admin role"""
    return user.is_superuser or user.role == "admin"


@login_required
@user_passes_test(is_admin_user)
def view_activity_logs(request):
    """
    Activity Log dashboard with advanced filtering and search.
    Shows recent admin activities with pagination.
    """
    # Base queryset
    logs = ActivityLog.objects.select_related("user").all()

    # Get filter parameters
    action_filter = request.GET.get("action", "")
    user_filter = request.GET.get("user", "")
    content_type_filter = request.GET.get("content_type", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    search_query = request.GET.get("search", "").strip()
    success_filter = request.GET.get("success", "")

    # Apply filters
    if action_filter:
        logs = logs.filter(action=action_filter)

    if user_filter:
        logs = logs.filter(user_id=user_filter)

    if content_type_filter:
        logs = logs.filter(content_type__icontains=content_type_filter)

    if date_from:
        try:
            from_date = timezone.datetime.strptime(date_from, "%Y-%m-%d")
            logs = logs.filter(timestamp__gte=from_date)
        except ValueError:
            pass

    if date_to:
        try:
            to_date = timezone.datetime.strptime(date_to, "%Y-%m-%d")
            # Include the entire day
            to_date = to_date + timedelta(days=1)
            logs = logs.filter(timestamp__lt=to_date)
        except ValueError:
            pass

    if search_query:
        logs = logs.filter(
            Q(description__icontains=search_query)
            | Q(object_repr__icontains=search_query)
            | Q(object_id__icontains=search_query)
        )

    if success_filter:
        logs = logs.filter(success=(success_filter == "true"))

    # Statistics
    total_logs = logs.count()
    today_logs = logs.filter(timestamp__gte=timezone.now().date()).count()
    failed_logs = logs.filter(success=False).count()
    unique_users = logs.values("user").distinct().count()

    # Get action counts for chart/stats
    action_stats = (
        logs.values("action").annotate(count=Count("id")).order_by("-count")[:10]
    )

    # Limit to recent 500 logs for performance
    logs = logs[:500]

    # Get distinct values for dropdowns
    all_users = User.objects.filter(
        id__in=ActivityLog.objects.values_list("user_id", flat=True).distinct()
    ).order_by("first_name", "last_name")

    all_content_types = (
        ActivityLog.objects.values_list("content_type", flat=True)
        .distinct()
        .exclude(content_type="")
    )

    context = {
        "logs": logs,
        "stats": {
            "total": total_logs,
            "today": today_logs,
            "failed": failed_logs,
            "unique_users": unique_users,
        },
        "action_stats": action_stats,
        "action_choices": ActivityLog.ACTION_CHOICES,
        "all_users": all_users,
        "all_content_types": sorted(set(all_content_types)),
        "filters": {
            "action": action_filter,
            "user": user_filter,
            "content_type": content_type_filter,
            "date_from": date_from,
            "date_to": date_to,
            "search": search_query,
            "success": success_filter,
        },
    }

    return render(request, "settings_manager/activity_logs.html", context)


@login_required
@user_passes_test(is_admin_user)
def view_log_detail(request, log_id):
    """
    Detailed view of a single activity log entry.
    Shows all fields including changes, metadata, and context.
    """
    log = get_object_or_404(ActivityLog.objects.select_related("user"), id=log_id)

    # Parse changes JSON if exists
    changes_formatted = None
    if log.changes:
        changes_formatted = json.dumps(log.changes, indent=2)

    context = {
        "log": log,
        "changes_formatted": changes_formatted,
    }

    return render(request, "settings_manager/log_detail.html", context)


@login_required
@user_passes_test(is_admin_user)
def export_logs(request):
    """
    Export activity logs to CSV or JSON format.
    Respects all current filters from the request.
    """
    export_format = request.GET.get("format", "csv")

    # Apply same filters as view_activity_logs
    logs = ActivityLog.objects.select_related("user").all()

    action_filter = request.GET.get("action", "")
    user_filter = request.GET.get("user", "")
    content_type_filter = request.GET.get("content_type", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    search_query = request.GET.get("search", "").strip()
    success_filter = request.GET.get("success", "")

    if action_filter:
        logs = logs.filter(action=action_filter)
    if user_filter:
        logs = logs.filter(user_id=user_filter)
    if content_type_filter:
        logs = logs.filter(content_type__icontains=content_type_filter)
    if date_from:
        try:
            from_date = timezone.datetime.strptime(date_from, "%Y-%m-%d")
            logs = logs.filter(timestamp__gte=from_date)
        except ValueError:
            pass
    if date_to:
        try:
            to_date = timezone.datetime.strptime(date_to, "%Y-%m-%d")
            to_date = to_date + timedelta(days=1)
            logs = logs.filter(timestamp__lt=to_date)
        except ValueError:
            pass
    if search_query:
        logs = logs.filter(
            Q(description__icontains=search_query)
            | Q(object_repr__icontains=search_query)
            | Q(object_id__icontains=search_query)
        )
    if success_filter:
        logs = logs.filter(success=(success_filter == "true"))

    # Limit export to 10,000 records
    logs = logs[:10000]

    if export_format == "json":
        # Export as JSON
        data = []
        for log in logs:
            data.append(
                {
                    "id": log.id,
                    "user": log.user.get_full_name() if log.user else "System",
                    "user_email": log.user.email if log.user else "",
                    "action": log.get_action_display(),
                    "content_type": log.content_type,
                    "object_id": log.object_id,
                    "object_repr": log.object_repr,
                    "description": log.description,
                    "ip_address": log.ip_address,
                    "device_name": log.device_name,
                    "location": log.location,
                    "timestamp": log.timestamp.isoformat(),
                    "success": log.success,
                    "error_message": log.error_message,
                    "changes": log.changes,
                }
            )

        response = HttpResponse(
            json.dumps(data, indent=2), content_type="application/json"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="activity_logs_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'
        )
        return response

    else:
        # Export as CSV
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="activity_logs_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(
            [
                "ID",
                "Timestamp",
                "User",
                "Email",
                "Action",
                "Content Type",
                "Object ID",
                "Object",
                "Description",
                "IP Address",
                "Device",
                "Location",
                "Success",
                "Error Message",
            ]
        )

        for log in logs:
            writer.writerow(
                [
                    log.id,
                    log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    log.user.get_full_name() if log.user else "System",
                    log.user.email if log.user else "",
                    log.get_action_display(),
                    log.content_type,
                    log.object_id,
                    log.object_repr,
                    log.description,
                    log.ip_address or "",
                    log.device_name or "",
                    log.location or "",
                    "Yes" if log.success else "No",
                    log.error_message or "",
                ]
            )

        return response


@login_required
@user_passes_test(is_admin_user)
def delete_old_logs(request):
    """
    Delete activity logs older than specified days.
    POST only for safety.
    """
    if request.method == "POST":
        days = int(request.POST.get("days", 90))
        cutoff_date = timezone.now() - timedelta(days=days)

        deleted_count, _ = ActivityLog.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()

        return JsonResponse(
            {
                "success": True,
                "deleted_count": deleted_count,
                "message": f"Deleted {deleted_count} logs older than {days} days",
            }
        )

    return JsonResponse({"success": False, "message": "POST request required"})
