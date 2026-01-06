"""
Admin views for system maintenance and backup management.
"""

import secrets
import string

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from system_maintenance.models import (
    BackupRecord,
    FactoryResetLog,
    MaintenanceMode,
    RestorePoint,
    SystemHealthCheck,
)
from system_maintenance.services.backup_service import BackupService
from system_maintenance.services.health_check_service import HealthCheckService
from system_maintenance.services.restore_service import RestoreService


def is_admin_user(user):
    """Check if user is admin or superuser"""
    return user.is_superuser or user.role in ["admin"]


@login_required
@user_passes_test(is_admin_user)
def maintenance_dashboard(request):
    """Main system maintenance dashboard"""
    # Get latest health check
    latest_health_check = SystemHealthCheck.objects.first()

    # Get backup statistics
    backup_service = BackupService()
    backup_stats = backup_service.get_backup_statistics()

    # Get maintenance mode status
    maintenance_active = MaintenanceMode.is_maintenance_active()
    latest_maintenance = None
    if maintenance_active:
        try:
            latest_maintenance = MaintenanceMode.objects.latest()
        except MaintenanceMode.DoesNotExist:
            pass

    # Recent backups
    recent_backups = BackupRecord.objects.all()[:5]

    # Recent health checks
    recent_health_checks = SystemHealthCheck.objects.all()[:5]

    context = {
        "latest_health_check": latest_health_check,
        "backup_stats": backup_stats,
        "maintenance_active": maintenance_active,
        "latest_maintenance": latest_maintenance,
        "recent_backups": recent_backups,
        "recent_health_checks": recent_health_checks,
    }

    return render(request, "system_maintenance/dashboard.html", context)


@login_required
@user_passes_test(is_admin_user)
def backup_management(request):
    """Backup management interface"""
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create":
            backup_type = request.POST.get("backup_type", "full")
            description = request.POST.get("description", "")

            try:
                backup_service = BackupService()
                backup = backup_service.create_backup(
                    backup_type=backup_type, user=request.user, description=description
                )
                messages.success(
                    request, f"Backup created successfully: {backup.backup_id}"
                )
            except Exception as e:
                messages.error(request, f"Backup failed: {str(e)}")

        elif action == "verify_backup":
            backup_id = request.POST.get("backup_id")
            backup = get_object_or_404(BackupRecord, backup_id=backup_id)

            backup_service = BackupService()
            success, message = backup_service.verify_backup(backup)

            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)

        elif action == "protect_backup":
            backup_id = request.POST.get("backup_id")
            backup = get_object_or_404(BackupRecord, backup_id=backup_id)
            backup.is_protected = True
            backup.save()
            messages.success(request, "Backup protected from auto-deletion")

        elif action == "delete_backup":
            backup_id = request.POST.get("backup_id")
            backup = get_object_or_404(BackupRecord, backup_id=backup_id)

            if backup.is_protected:
                messages.error(request, "Cannot delete protected backup")
            else:
                # Delete files
                if backup.database_file:
                    backup.database_file.delete()
                if backup.media_archive:
                    backup.media_archive.delete()
                if backup.settings_file:
                    backup.settings_file.delete()

                backup.delete()
                messages.success(request, "Backup deleted successfully")

        return redirect("system_maintenance:backup_management")

    # GET request
    backups = BackupRecord.objects.all().order_by("-created_at")

    # Add display name for created_by
    for backup in backups:
        if backup.created_by:
            backup.created_by_display = (
                backup.created_by.get_full_name() or backup.created_by.username
            )
        else:
            backup.created_by_display = "System"

    # Pagination
    page_number = request.GET.get("page", 1)
    paginator = Paginator(backups, 10)  # Show 10 backups per page
    page_obj = paginator.get_page(page_number)

    # Statistics
    total_backups = backups.count()
    total_size = (
        backups.filter(status="completed").aggregate(total=Sum("file_size_bytes"))[
            "total"
        ]
        or 0
    )

    context = {
        "backups": page_obj,
        "total_backups": total_backups,
        "total_size_bytes": total_size,
        "page_obj": page_obj,
        "paginator": paginator,
    }

    return render(request, "system_maintenance/backup_management.html", context)


@login_required
@user_passes_test(is_admin_user)
def download_backup(request, backup_id):
    """Download backup files"""
    backup = get_object_or_404(BackupRecord, backup_id=backup_id)

    # Only allow download of completed backups
    if backup.status != "completed":
        raise Http404("Backup not available for download")

    download_type = request.GET.get("type")
    if not download_type:
        raise Http404("Download type not specified")

    if download_type == "database":
        if not backup.database_file:
            raise Http404("Database file not available")
        file_field = backup.database_file
        filename = f"database_{backup.backup_id}.json"

    elif download_type == "media":
        if not backup.media_archive:
            raise Http404("Media archive not available")
        file_field = backup.media_archive
        filename = f"media_{backup.backup_id}.zip"

    elif download_type == "settings":
        if not backup.settings_file:
            raise Http404("Settings file not available")
        file_field = backup.settings_file
        filename = f"settings_{backup.backup_id}.json"

    else:
        raise Http404("Invalid download type")

    # Return file response
    response = FileResponse(file_field.open(), as_attachment=True, filename=filename)
    response["Content-Type"] = "application/octet-stream"
    return response


@login_required
@user_passes_test(is_admin_user)
def restore_management(request):
    """Restore point management"""
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create_restore_point":
            backup_id = request.POST.get("backup_id")
            name = request.POST.get("name")
            description = request.POST.get("description", "")

            backup = get_object_or_404(BackupRecord, backup_id=backup_id)

            restore_service = RestoreService()
            restore_point = restore_service.create_restore_point(
                backup=backup, name=name, description=description, user=request.user
            )

            messages.success(request, f"Restore point created: {restore_point.name}")

        elif action == "restore_from_point":
            restore_point_id = request.POST.get("restore_point_id")
            restore_point = get_object_or_404(
                RestorePoint, restore_point_id=restore_point_id
            )

            # Validate
            restore_service = RestoreService()
            valid, message = restore_service.validate_restore_point(restore_point)

            if not valid:
                messages.error(request, f"Cannot restore: {message}")
                return redirect("system_maintenance:restore_management")

            # Confirm with user (this should have a confirmation page in production)
            restore_database = request.POST.get("restore_database") == "on"
            restore_media = request.POST.get("restore_media") == "on"

            try:
                success, message = restore_service.restore_from_backup(
                    backup_record=restore_point.backup,
                    restore_database=restore_database,
                    restore_media=restore_media,
                    user=request.user,
                )

                if success:
                    # Update restore point
                    restore_point.last_restored_at = timezone.now()
                    restore_point.last_restored_by = request.user
                    restore_point.restore_count += 1
                    restore_point.save()

                    messages.success(request, message)
                else:
                    messages.error(request, message)
            except Exception as e:
                messages.error(request, f"Restore failed: {str(e)}")

        return redirect("system_maintenance:restore_management")

    # GET request
    restore_points = RestorePoint.objects.select_related("backup", "created_by").all()
    available_backups = BackupRecord.objects.filter(
        status__in=["completed", "verified"]
    ).order_by("-created_at")

    context = {
        "restore_points": restore_points,
        "available_backups": available_backups,
    }

    return render(request, "system_maintenance/restore_management.html", context)


@login_required
@user_passes_test(is_admin_user)
def health_check(request):
    """Perform and display system health check"""
    if request.method == "POST":
        health_service = HealthCheckService()
        health_check = health_service.perform_health_check(user=request.user)

        messages.success(
            request, f"Health check completed. Score: {health_check.health_score}%"
        )
        return redirect(
            "system_maintenance:health_check_detail", check_id=health_check.check_id
        )

    # GET request - show recent health checks
    health_checks = SystemHealthCheck.objects.all()[:20]
    latest_check = health_checks.first() if health_checks else None

    context = {
        "health_checks": health_checks,
        "latest_check": latest_check,
    }

    return render(request, "system_maintenance/health_check.html", context)


@login_required
@user_passes_test(is_admin_user)
def health_check_detail(request, check_id):
    """Display detailed health check results"""
    health_check = get_object_or_404(SystemHealthCheck, check_id=check_id)

    context = {
        "health_check": health_check,
    }

    return render(request, "system_maintenance/health_check_detail.html", context)


@login_required
@user_passes_test(is_admin_user)
def maintenance_mode_control(request):
    """Control maintenance mode"""
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "activate":
            reason = request.POST.get("reason")
            duration = int(request.POST.get("duration_minutes", 30))
            create_backup = request.POST.get("create_backup") == "on"
            custom_message = request.POST.get("custom_message", "")

            # Create pre-maintenance backup if requested
            backup = None
            if create_backup:
                try:
                    backup_service = BackupService()
                    backup = backup_service.create_backup(
                        backup_type="pre_maintenance",
                        user=request.user,
                        description="Automatic backup before maintenance",
                    )
                except Exception as e:
                    messages.warning(
                        request,
                        f"Backup failed: {str(e)}. Continuing with maintenance activation.",
                    )

            # Activate maintenance mode
            maintenance = MaintenanceMode.objects.create()
            maintenance.activate(
                user=request.user,
                reason=reason,
                duration_minutes=duration,
                backup=backup,
            )
            maintenance.custom_message = custom_message
            maintenance.save()

            messages.warning(
                request,
                "Maintenance mode activated. Non-admin users cannot access the system.",
            )

        elif action == "deactivate":
            try:
                maintenance = MaintenanceMode.objects.latest()
                if maintenance.is_active:
                    notes = request.POST.get("notes", "")
                    success = request.POST.get("success") == "on"

                    maintenance.deactivate(
                        user=request.user, success=success, notes=notes
                    )
                    messages.success(request, "Maintenance mode deactivated")
            except MaintenanceMode.DoesNotExist:
                messages.error(request, "No active maintenance mode found")

        return redirect("system_maintenance:maintenance_mode")

    # GET request
    maintenance_active = MaintenanceMode.is_maintenance_active()
    current_maintenance = None
    maintenance_history = MaintenanceMode.objects.all()[:10]

    if maintenance_active:
        try:
            current_maintenance = MaintenanceMode.objects.latest()
        except MaintenanceMode.DoesNotExist:
            pass

    context = {
        "maintenance_active": maintenance_active,
        "current_maintenance": current_maintenance,
        "maintenance_history": maintenance_history,
    }

    return render(request, "system_maintenance/maintenance_mode.html", context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def factory_reset(request):
    """
    Factory reset interface - SUPERUSER ONLY
    Requires confirmation code for safety
    """
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "initiate_reset":
            # Generate confirmation code
            confirmation_code = "".join(
                secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8)
            )

            # Create reset log
            reset_log = FactoryResetLog.objects.create(
                reset_id=f"reset_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
                initiated_by=request.user,
                confirmation_code=confirmation_code,
                reset_database=request.POST.get("reset_database") == "on",
                reset_media_files=request.POST.get("reset_media") == "on",
                reset_settings=request.POST.get("reset_settings") == "on",
                keep_users=request.POST.get("keep_users") == "on",
                keep_organizations=request.POST.get("keep_orgs") == "on",
            )

            # Create mandatory backup before reset
            try:
                backup_service = BackupService()
                backup = backup_service.create_backup(
                    backup_type="pre_reset",
                    user=request.user,
                    description="CRITICAL: Pre-factory reset backup",
                )
                backup.is_protected = True
                backup.save()

                reset_log.pre_reset_backup = backup
                reset_log.recovery_backup_id = backup.backup_id
                reset_log.save()

                messages.warning(
                    request,
                    f"Factory reset initiated. Backup created: {backup.backup_id}. "
                    f"CONFIRMATION CODE: {confirmation_code}. Please copy this code to proceed.",
                )

                # Store reset_id in session for confirmation
                request.session["pending_reset_id"] = reset_log.reset_id

            except Exception as e:
                reset_log.status = "failed"
                reset_log.error_message = f"Pre-reset backup failed: {str(e)}"
                reset_log.save()
                messages.error(request, f"Cannot proceed: {str(e)}")

        elif action == "confirm_reset":
            reset_id = request.session.get("pending_reset_id")
            entered_code = request.POST.get("confirmation_code", "").strip().upper()

            if not reset_id:
                messages.error(request, "No pending reset found")
                return redirect("system_maintenance:factory_reset")

            reset_log = get_object_or_404(FactoryResetLog, reset_id=reset_id)

            if entered_code != reset_log.confirmation_code:
                messages.error(request, "Invalid confirmation code")
                return redirect("system_maintenance:factory_reset")

            # Execute factory reset
            reset_log.confirmed_at = timezone.now()
            reset_log.status = "in_progress"
            reset_log.save()

            try:
                # THIS IS DANGEROUS - actual implementation should be more sophisticated
                messages.error(
                    request,
                    "FACTORY RESET EXECUTION NOT IMPLEMENTED. "
                    "This would delete all data. Please implement carefully with additional safeguards.",
                )
                reset_log.status = "failed"
                reset_log.error_message = "Not implemented for safety"
                reset_log.save()

            except Exception as e:
                reset_log.status = "failed"
                reset_log.error_message = str(e)
                reset_log.save()
                messages.error(request, f"Reset failed: {str(e)}")

            # Clear session
            if "pending_reset_id" in request.session:
                del request.session["pending_reset_id"]

        return redirect("system_maintenance:factory_reset")

    # GET request
    pending_reset_id = request.session.get("pending_reset_id")
    pending_reset = None

    if pending_reset_id:
        try:
            pending_reset = FactoryResetLog.objects.get(reset_id=pending_reset_id)
        except FactoryResetLog.DoesNotExist:
            del request.session["pending_reset_id"]

    reset_history = FactoryResetLog.objects.all()[:10]

    context = {
        "pending_reset": pending_reset,
        "reset_history": reset_history,
    }

    return render(request, "system_maintenance/factory_reset.html", context)


@login_required
@user_passes_test(is_admin_user)
def download_backup(request, backup_id):
    """Download a backup file"""
    backup = get_object_or_404(BackupRecord, backup_id=backup_id)
    file_type = request.GET.get("type", "database")

    if file_type == "database" and backup.database_file:
        return FileResponse(
            backup.database_file.open("rb"),
            as_attachment=True,
            filename=f"{backup.backup_id}_database.json",
        )
    elif file_type == "media" and backup.media_archive:
        return FileResponse(
            backup.media_archive.open("rb"),
            as_attachment=True,
            filename=f"{backup.backup_id}_media.zip",
        )
    elif file_type == "settings" and backup.settings_file:
        return FileResponse(
            backup.settings_file.open("rb"),
            as_attachment=True,
            filename=f"{backup.backup_id}_settings.json",
        )

    raise Http404("Backup file not found")
