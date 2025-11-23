"""
Management command for creating scheduled backups.
Use with cron/Task Scheduler for automated backups.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from system_maintenance.services.backup_service import BackupService
from system_maintenance.services.health_check_service import HealthCheckService
import sys


class Command(BaseCommand):
    help = 'Create a scheduled backup with optional health check'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            default='full',
            choices=['full', 'database_only', 'media_only', 'incremental'],
            help='Type of backup to create'
        )
        parser.add_argument(
            '--health-check',
            action='store_true',
            help='Run health check before backup'
        )
        parser.add_argument(
            '--cleanup',
            type=int,
            default=30,
            help='Clean up backups older than N days (default: 30)'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Username to associate with backup (default: first superuser)'
        )
    
    def handle(self, *args, **options):
        User = get_user_model()
        
        # Get user for backup
        if options['user']:
            try:
                user = User.objects.get(username=options['user'])
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User {options["user"]} not found'))
                user = None
        else:
            # Use first superuser
            user = User.objects.filter(is_superuser=True).first()
        
        # Run health check if requested
        if options['health_check']:
            self.stdout.write('Running health check...')
            try:
                health_service = HealthCheckService()
                health_check = health_service.perform_health_check(user=user)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Health check completed: Score {health_check.health_score}%, '
                        f'Status: {health_check.overall_status}'
                    )
                )
                
                if health_check.critical_issues:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Critical issues found: {len(health_check.critical_issues)}'
                        )
                    )
                    for issue in health_check.critical_issues:
                        self.stdout.write(f'  - {issue}')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Health check failed: {str(e)}'))
        
        # Create backup
        self.stdout.write(f'Creating {options["type"]} backup...')
        try:
            backup_service = BackupService()
            backup = backup_service.create_backup(
                backup_type=options['type'],
                user=user,
                description='Scheduled backup via management command'
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Backup created successfully: {backup.backup_id}\n'
                    f'Size: {backup.get_size_display()}\n'
                    f'Status: {backup.status}'
                )
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Backup failed: {str(e)}'))
            sys.exit(1)
        
        # Cleanup old backups
        if options['cleanup']:
            self.stdout.write(f'Cleaning up backups older than {options["cleanup"]} days...')
            try:
                deleted_count = backup_service.cleanup_old_backups(
                    retention_days=options['cleanup'],
                    keep_protected=True
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Deleted {deleted_count} old backups')
                )
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Cleanup failed: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS('Scheduled backup completed successfully'))
