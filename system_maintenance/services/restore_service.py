"""
Restore service for recovering system from backups.
"""

import os
import json
import zipfile
import shutil
import tempfile
from pathlib import Path
from django.conf import settings
from django.core.management import call_command
from django.db import transaction, connection
from django.utils import timezone
from system_maintenance.models import BackupRecord, RestorePoint
import subprocess


class RestoreService:
    """
    Service for restoring system from backups with validation and rollback.
    """

    def __init__(self):
        self.backup_dir = Path(settings.MEDIA_ROOT) / "backups"

    def create_restore_point(self, backup, name, description="", user=None):
        """
        Create a restore point from a backup.

        Args:
            backup: BackupRecord instance
            name: Name for the restore point
            description: Optional description
            user: User creating the restore point

        Returns:
            RestorePoint instance
        """
        from django.contrib.auth import get_user_model

        User = get_user_model()

        restore_point_id = (
            f"restore_{timezone.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        )

        # Capture current system state
        system_state = {
            "current_record_counts": self._get_current_record_counts(),
            "active_users_count": User.objects.filter(is_active=True).count(),
            "database_size": self._get_database_size(),
            "timestamp": timezone.now().isoformat(),
        }

        restore_point = RestorePoint.objects.create(
            restore_point_id=restore_point_id,
            name=name,
            description=description,
            backup=backup,
            created_by=user,
            system_state=system_state,
            is_automatic=False,
        )

        return restore_point

    def restore_from_backup(
        self, backup_record, restore_database=True, restore_media=True, user=None
    ):
        """
        Restore system from a backup.

        Args:
            backup_record: BackupRecord to restore from
            restore_database: Whether to restore database
            restore_media: Whether to restore media files
            user: User performing the restore

        Returns:
            (success: bool, message: str)
        """
        if backup_record.status != "completed" and backup_record.status != "verified":
            return False, "Can only restore from completed/verified backups"

        # Create automatic restore point before restoring
        from system_maintenance.services.backup_service import BackupService

        backup_service = BackupService()

        try:
            # Create pre-restore backup
            pre_restore_backup = backup_service.create_backup(
                backup_type="pre_reset",
                user=user,
                description=f"Automatic backup before restoring from {backup_record.backup_id}",
            )

            # Restore database
            if restore_database and backup_record.database_file:
                success, message = self._restore_database(backup_record)
                if not success:
                    return False, f"Database restore failed: {message}"

            # Restore media files
            if restore_media and backup_record.media_archive:
                success, message = self._restore_media(backup_record)
                if not success:
                    return False, f"Media restore failed: {message}"

            return True, "Restore completed successfully"

        except Exception as e:
            return False, f"Restore failed: {str(e)}"

    def _restore_database(self, backup_record):
        """Restore database from backup"""
        try:
            # Open and load the backup file
            backup_record.database_file.open("r")

            # Create temp file
            temp_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            )

            try:
                # Copy backup data to temp file
                backup_data = backup_record.database_file.read()
                temp_file.write(backup_data)
                temp_file.close()

                backup_record.database_file.close()

                # Flush existing data (dangerous!)
                # First, get list of all app models to flush
                from django.apps import apps

                with transaction.atomic():
                    # Disable foreign key checks temporarily
                    with connection.cursor() as cursor:
                        # For PostgreSQL
                        if "postgresql" in settings.DATABASES["default"]["ENGINE"]:
                            cursor.execute("SET CONSTRAINTS ALL DEFERRED")
                        # For SQLite
                        elif "sqlite" in settings.DATABASES["default"]["ENGINE"]:
                            cursor.execute("PRAGMA foreign_keys = OFF")

                    # Call loaddata
                    call_command("loaddata", temp_file.name, verbosity=0)

                    # Re-enable foreign key checks
                    with connection.cursor() as cursor:
                        if "sqlite" in settings.DATABASES["default"]["ENGINE"]:
                            cursor.execute("PRAGMA foreign_keys = ON")

                return True, "Database restored successfully"

            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)

        except Exception as e:
            return False, str(e)

    def _restore_media(self, backup_record):
        """Restore media files from backup"""
        try:
            media_root = Path(settings.MEDIA_ROOT)

            # Open backup archive
            backup_record.media_archive.open("rb")

            # Create temp file
            temp_zip = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)

            try:
                # Copy archive to temp file
                temp_zip.write(backup_record.media_archive.read())
                temp_zip.close()

                backup_record.media_archive.close()

                # Extract files
                with zipfile.ZipFile(temp_zip.name, "r") as zipf:
                    # Extract all files
                    for member in zipf.namelist():
                        # Skip backup directories
                        if "backups" in member:
                            continue

                        target_path = media_root / member

                        # Create parent directories
                        target_path.parent.mkdir(parents=True, exist_ok=True)

                        # Extract file
                        with zipf.open(member) as source, open(
                            target_path, "wb"
                        ) as target:
                            shutil.copyfileobj(source, target)

                return True, "Media files restored successfully"

            finally:
                if os.path.exists(temp_zip.name):
                    os.unlink(temp_zip.name)

        except Exception as e:
            return False, str(e)

    def validate_restore_point(self, restore_point):
        """Validate a restore point can be used"""
        backup = restore_point.backup

        # Check backup exists and is valid
        if backup.status not in ["completed", "verified"]:
            return False, "Associated backup is not in valid state"

        # Check files exist
        if backup.database_file and not backup.database_file.storage.exists(
            backup.database_file.name
        ):
            return False, "Database backup file missing"

        if backup.media_archive and not backup.media_archive.storage.exists(
            backup.media_archive.name
        ):
            return False, "Media backup file missing"

        return True, "Restore point is valid"

    def _get_current_record_counts(self):
        """Get current record counts for all models"""
        from django.apps import apps

        counts = {}
        for model in apps.get_models():
            if model._meta.app_label in ["contenttypes", "sessions", "admin"]:
                continue

            try:
                model_name = f"{model._meta.app_label}.{model._meta.model_name}"
                counts[model_name] = model.objects.count()
            except Exception:
                continue

        return counts

    def _get_database_size(self):
        """Get approximate database size"""
        try:
            with connection.cursor() as cursor:
                if "postgresql" in settings.DATABASES["default"]["ENGINE"]:
                    cursor.execute("SELECT pg_database_size(current_database())")
                    return cursor.fetchone()[0]
                elif "sqlite" in settings.DATABASES["default"]["ENGINE"]:
                    db_path = settings.DATABASES["default"]["NAME"]
                    if os.path.exists(db_path):
                        return os.path.getsize(db_path)
            return 0
        except Exception:
            return 0

    def get_restore_preview(self, backup_record):
        """
        Preview what will be restored from a backup.

        Returns comparison between current state and backup state.
        """
        current_counts = self._get_current_record_counts()
        backup_counts = backup_record.records_count

        comparison = {
            "current": current_counts,
            "backup": backup_counts,
            "differences": {},
        }

        # Calculate differences
        all_models = set(current_counts.keys()) | set(backup_counts.keys())

        for model in all_models:
            current = current_counts.get(model, 0)
            backup = backup_counts.get(model, 0)

            if current != backup:
                comparison["differences"][model] = {
                    "current": current,
                    "backup": backup,
                    "change": backup - current,
                }

        return comparison
