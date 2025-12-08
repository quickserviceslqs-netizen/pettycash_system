"""
Backup service for creating and managing system backups.
"""
import os
import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from django.conf import settings
from django.core.management import call_command
from django.db import connection, models
from django.utils import timezone
from django.apps import apps
from system_maintenance.models import BackupRecord
import sys
import platform


class BackupService:
    """
    Comprehensive backup service for database, media files, and settings.
    """
    
    def __init__(self):
        self.backup_dir = Path(settings.MEDIA_ROOT) / 'backups'
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, backup_type='full', user=None, description=''):
        """
        Create a new backup of specified type.
        
        Args:
            backup_type: Type of backup (full, database_only, media_only, etc.)
            user: User creating the backup
            description: Optional description
        
        Returns:
            BackupRecord instance
        """
        # Generate unique backup ID
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        
        # Create backup record
        backup_record = BackupRecord.objects.create(
            backup_id=backup_id,
            backup_type=backup_type,
            status='in_progress',
            created_by=user,
            description=description,
            system_version=getattr(settings, 'VERSION', '1.0.0'),
            django_version='.'.join(map(str, [*__import__('django').VERSION[:3]])),
            python_version=sys.version.split()[0],
        )
        
        try:
            # Perform backup based on type
            if backup_type in ['full', 'database_only', 'pre_maintenance', 'pre_reset', 'manual', 'scheduled']:
                self._backup_database(backup_record)
            
            if backup_type in ['full', 'media_only']:
                self._backup_media_files(backup_record)
            
            if backup_type in ['full', 'settings_only', 'pre_reset']:
                self._backup_settings(backup_record)
            
            # Get record counts
            backup_record.records_count = self._get_record_counts()
            
            # Calculate total size
            total_size = 0
            if backup_record.database_file:
                total_size += backup_record.database_size_bytes
            if backup_record.media_archive:
                total_size += backup_record.media_size_bytes
            backup_record.file_size_bytes = total_size
            
            # Mark as completed
            backup_record.mark_completed()
            
            return backup_record
            
        except Exception as e:
            backup_record.mark_failed(str(e))
            raise
    
    def _backup_database(self, backup_record):
        """Backup database to JSON dump"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        try:
            # Use Django's dumpdata command
            with open(temp_file.name, 'w', encoding='utf-8') as f:
                call_command(
                    'dumpdata',
                    exclude=[
                        'contenttypes',
                        'auth.permission',
                        'sessions.session',
                        'admin.logentry',
                    ],
                    indent=2,
                    stdout=f
                )
            
            # Get file size
            file_size = os.path.getsize(temp_file.name)
            backup_record.database_size_bytes = file_size
            
            # Save to backup record
            filename = f"database_{backup_record.backup_id}.json"
            with open(temp_file.name, 'rb') as f:
                backup_record.database_file.save(filename, f, save=True)
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
    def _backup_media_files(self, backup_record):
        """Backup media files to compressed archive"""
        media_root = Path(settings.MEDIA_ROOT)
        
        # Skip if no media files
        if not media_root.exists():
            return
        
        temp_zip = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
        
        try:
            with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add all media files except backups directory
                for file_path in media_root.rglob('*'):
                    if file_path.is_file() and 'backups' not in file_path.parts:
                        arcname = file_path.relative_to(media_root)
                        zipf.write(file_path, arcname)
            
            # Get file size
            file_size = os.path.getsize(temp_zip.name)
            backup_record.media_size_bytes = file_size
            
            # Save to backup record
            filename = f"media_{backup_record.backup_id}.zip"
            with open(temp_zip.name, 'rb') as f:
                backup_record.media_archive.save(filename, f, save=True)
        
        finally:
            if os.path.exists(temp_zip.name):
                os.unlink(temp_zip.name)
    
    def _backup_settings(self, backup_record):
        """Backup critical settings and configurations"""
        from settings_manager.models import SystemSetting
        
        settings_data = {
            'system_settings': list(SystemSetting.objects.all().values()),
            'installed_apps': settings.INSTALLED_APPS,
            'database_engine': settings.DATABASES['default']['ENGINE'],
            'time_zone': settings.TIME_ZONE,
            'language_code': settings.LANGUAGE_CODE,
            'backup_timestamp': timezone.now().isoformat(),
        }
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        try:
            with open(temp_file.name, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=2, default=str)
            
            filename = f"settings_{backup_record.backup_id}.json"
            with open(temp_file.name, 'rb') as f:
                backup_record.settings_file.save(filename, f, save=True)
        
        finally:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
    def _get_record_counts(self):
        """Get count of records for each model"""
        counts = {}
        
        for model in apps.get_models():
            # Skip some models
            if model._meta.app_label in ['contenttypes', 'sessions', 'admin']:
                continue
            
            try:
                model_name = f"{model._meta.app_label}.{model._meta.model_name}"
                counts[model_name] = model.objects.count()
            except Exception:
                continue
        
        return counts
    
    def verify_backup(self, backup_record):
        """Verify backup integrity"""
        try:
            # Check files exist
            if backup_record.database_file and not backup_record.database_file.storage.exists(backup_record.database_file.name):
                return False, "Database backup file not found"
            
            if backup_record.media_archive and not backup_record.media_archive.storage.exists(backup_record.media_archive.name):
                return False, "Media backup file not found"
            
            # Check file sizes match
            if backup_record.database_file:
                actual_size = backup_record.database_file.size
                if actual_size != backup_record.database_size_bytes:
                    return False, f"Database file size mismatch: expected {backup_record.database_size_bytes}, got {actual_size}"
            
            # Verify database backup is valid JSON
            if backup_record.database_file:
                try:
                    backup_record.database_file.open('r')
                    data = json.load(backup_record.database_file)
                    backup_record.database_file.close()
                    
                    if not isinstance(data, list):
                        return False, "Database backup is not valid JSON array"
                except json.JSONDecodeError as e:
                    return False, f"Database backup is corrupted: {str(e)}"
            
            # Update verification status
            backup_record.restore_tested = True
            backup_record.last_verified = timezone.now()
            backup_record.status = 'verified'
            backup_record.save()
            
            return True, "Backup verified successfully"
        
        except Exception as e:
            return False, f"Verification failed: {str(e)}"
    
    def cleanup_old_backups(self, retention_days=30, keep_protected=True):
        """
        Delete old backups based on retention policy.
        
        Args:
            retention_days: Number of days to keep backups
            keep_protected: Don't delete protected backups
        """
        cutoff_date = timezone.now() - timedelta(days=retention_days)
        
        old_backups = BackupRecord.objects.filter(
            created_at__lt=cutoff_date,
            status='completed'
        )
        
        if keep_protected:
            old_backups = old_backups.filter(is_protected=False)
        
        deleted_count = 0
        for backup in old_backups:
            try:
                # Delete files
                if backup.database_file:
                    backup.database_file.delete()
                if backup.media_archive:
                    backup.media_archive.delete()
                if backup.settings_file:
                    backup.settings_file.delete()
                
                # Delete record
                backup.delete()
                deleted_count += 1
            except Exception:
                continue
        
        return deleted_count
    
    def get_backup_statistics(self):
        """Get backup statistics"""
        total_backups = BackupRecord.objects.count()
        successful_backups = BackupRecord.objects.filter(status='completed').count()
        failed_backups = BackupRecord.objects.filter(status='failed').count()
        total_size = BackupRecord.objects.filter(status='completed').aggregate(
            total=models.Sum('file_size_bytes')
        )['total'] or 0
        
        latest_backup = BackupRecord.objects.filter(status='completed').first()
        
        return {
            'total_backups': total_backups,
            'successful_backups': successful_backups,
            'failed_backups': failed_backups,
            'total_size_bytes': total_size,
            'latest_backup': latest_backup,
            'oldest_backup': BackupRecord.objects.filter(status='completed').last(),
        }
