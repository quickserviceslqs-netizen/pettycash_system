# Real-Time Backup System Guide

## Overview

The real-time backup system automatically creates backups when critical operations occur in your petty cash system. This provides an additional layer of data protection beyond manual and scheduled backups.

## Features

### 1. Automatic Trigger Events

Real-time backups are automatically created when:

#### **High-Value Transactions**
- Requisition approved with amount ≥ $10,000
- Payment created/disbursed with amount ≥ $10,000

#### **Critical User Operations**
- Superuser account created
- Staff/superuser account deleted

#### **Data Deletion**
- Approved/completed requisition deleted
- Payment deleted
- Company deleted
- Department with users deleted

#### **System Configuration Changes**
- Critical settings modified:
  - Approval threshold (Manager)
  - Approval threshold (CFO)
  - Default currency
  - Multi-currency settings
- Approval threshold rules modified or deleted

### 2. Intelligent Cooldown System

To prevent backup storms and performance issues:
- **Default cooldown**: 30 minutes between real-time backups
- If multiple events occur within cooldown period, only the first triggers a backup
- Prevents infinite loops when backups themselves trigger signals

### 3. Database-Only Backups

Real-time backups use `database_only` type for speed:
- Faster than full backups
- Captures all critical transaction data
- Ideal for point-in-time recovery
- Media files backed up separately on schedule

## Configuration

### Settings (add to `settings.py`)

```python
# Real-time backup cooldown in minutes (default: 30)
REALTIME_BACKUP_COOLDOWN = 30

# Minimum amount to trigger backup for transactions (default: 10000)
REALTIME_BACKUP_AMOUNT_THRESHOLD = 10000
```

### Customizing Triggers

Edit `system_maintenance/signals.py` to:
- Add new trigger events
- Modify thresholds
- Change backup types
- Add custom conditions

Example:
```python
@receiver(post_save, sender='transactions.Requisition')
def backup_on_requisition_approved(sender, instance, created, **kwargs):
    if not created and instance.status == 'approved':
        # Custom threshold
        if instance.amount >= 50000:  # Only backup $50k+
            realtime_backup_manager.create_realtime_backup(
                reason=f'Very high-value requisition: {instance.requisition_id}',
                user=instance.approved_by
            )
```

## Scheduled Backups

Use the management command for automated daily/weekly backups:

### Windows Task Scheduler

Create a scheduled task:

```powershell
# Daily full backup at 2 AM with health check
schtasks /create /tn "DailyPettyCashBackup" /tr "C:\Users\ADMIN\pettycash_system\venv\Scripts\python.exe C:\Users\ADMIN\pettycash_system\manage.py create_scheduled_backup --type full --health-check --cleanup 30" /sc daily /st 02:00

# Weekly media backup on Sundays at 3 AM
schtasks /create /tn "WeeklyMediaBackup" /tr "C:\Users\ADMIN\pettycash_system\venv\Scripts\python.exe C:\Users\ADMIN\pettycash_system\manage.py create_scheduled_backup --type media_only" /sc weekly /d SUN /st 03:00
```

### Linux Cron

Add to crontab:

```bash
# Daily full backup at 2 AM
0 2 * * * /path/to/venv/bin/python /path/to/manage.py create_scheduled_backup --type full --health-check --cleanup 30

# Weekly media backup on Sundays at 3 AM
0 3 * * 0 /path/to/venv/bin/python /path/to/manage.py create_scheduled_backup --type media_only
```

### Manual Command Usage

```bash
# Create full backup with health check
python manage.py create_scheduled_backup --type full --health-check

# Create database backup only
python manage.py create_scheduled_backup --type database_only

# Create backup and clean up old ones (keep last 30 days)
python manage.py create_scheduled_backup --type full --cleanup 30

# Create backup as specific user
python manage.py create_scheduled_backup --type full --user admin_username
```

## Monitoring Real-Time Backups

### View Backup Logs

Real-time backups are logged to Django's logging system:

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/realtime_backups.log',
        },
    },
    'loggers': {
        'system_maintenance.signals': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### Check Backup Dashboard

Visit: `/maintenance/` to see:
- Recent backups (including real-time ones)
- Backup statistics
- Latest health check results

### Identify Real-Time Backups

In backup management (`/maintenance/backups/`):
- Look for descriptions starting with "Real-time backup:"
- Filter by `database_only` type
- Check creation timestamps for frequent intervals

## Best Practices

### 1. Storage Management

Real-time backups can accumulate quickly:
- Set automatic cleanup with retention policy (30-90 days recommended)
- Use `--cleanup` flag in scheduled backups
- Protect critical backups manually

### 2. Performance Considerations

- **Default 30-minute cooldown** prevents performance impact
- Database-only backups are fast (< 10 seconds typically)
- Monitor disk space usage regularly
- Consider increasing cooldown for high-transaction environments

### 3. Threshold Tuning

Adjust `REALTIME_BACKUP_AMOUNT_THRESHOLD` based on your business:
- Small operations: $1,000 - $5,000
- Medium operations: $10,000 - $25,000
- Large operations: $50,000+

### 4. Testing Real-Time Backups

Test that signals work correctly:

```python
# Django shell
python manage.py shell

from django.contrib.auth import get_user_model
from transactions.models import Requisition
from decimal import Decimal

# Create high-value requisition
user = get_user_model().objects.first()
req = Requisition.objects.create(
    requested_by=user,
    amount=Decimal('15000.00'),
    description='Test high-value requisition',
    company=user.company
)

# Approve it (should trigger backup)
req.status = 'approved'
req.save()

# Check backups
from system_maintenance.models import BackupRecord
recent = BackupRecord.objects.first()
print(f"Latest backup: {recent.backup_id}")
print(f"Description: {recent.description}")
```

### 5. Backup Strategy

Combine all backup types for comprehensive protection:

1. **Real-time**: Automatic on critical events (database only)
2. **Scheduled**: Daily full backups (database + media + settings)
3. **Manual**: On-demand before major changes
4. **Pre-operation**: Automatic before maintenance/reset

## Troubleshooting

### Backups Not Triggering

1. **Check signals are registered**:
   ```python
   python manage.py shell
   from django.db.models import signals
   print(signals.post_save.receivers)
   ```

2. **Verify app is ready**:
   - Ensure `system_maintenance` in `INSTALLED_APPS`
   - Check `apps.py` has `ready()` method

3. **Check logs**:
   - Look for "Skipping backup: cooldown active"
   - Check for error messages

### Too Many Backups

1. **Increase cooldown**:
   ```python
   REALTIME_BACKUP_COOLDOWN = 60  # 1 hour
   ```

2. **Raise thresholds**:
   ```python
   REALTIME_BACKUP_AMOUNT_THRESHOLD = 50000
   ```

3. **Disable specific signals**:
   - Comment out signal decorators in `signals.py`

### Performance Issues

1. **Check backup frequency**:
   ```sql
   SELECT COUNT(*) FROM system_maintenance_backuprecord 
   WHERE created_at > NOW() - INTERVAL '1 hour';
   ```

2. **Optimize backup storage**:
   - Enable compression
   - Use external storage (S3, etc.)
   - Implement automatic cleanup

3. **Use async backups** (advanced):
   - Integrate with Celery
   - Queue backup tasks
   - Process in background workers

## Security Considerations

1. **Protected backups**: Real-time backups are NOT protected by default (to allow cleanup)
2. **Manual protection**: Protect critical backups via UI if needed
3. **Access control**: Only admins can view/download backups
4. **Audit trail**: All backups logged with reason and timestamp

## Integration Examples

### Celery Integration (Advanced)

For high-volume systems, use Celery for async backups:

```python
# tasks.py
from celery import shared_task

@shared_task
def async_realtime_backup(reason, user_id=None):
    from system_maintenance.signals import realtime_backup_manager
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    user = User.objects.get(id=user_id) if user_id else None
    
    return realtime_backup_manager.create_realtime_backup(reason, user)

# signals.py
from .tasks import async_realtime_backup

@receiver(post_save, sender='transactions.Requisition')
def backup_on_requisition_approved(sender, instance, created, **kwargs):
    if not created and instance.status == 'approved':
        if instance.amount >= 10000:
            async_realtime_backup.delay(
                reason=f'High-value requisition: {instance.requisition_id}',
                user_id=instance.approved_by.id if instance.approved_by else None
            )
```

### Notification Integration

Send notifications when backups are created:

```python
# Add to signals.py
from django.core.mail import mail_admins

def create_realtime_backup(self, reason, user=None):
    # ... existing code ...
    
    if backup:
        # Send notification
        mail_admins(
            subject='Real-Time Backup Created',
            message=f'Backup {backup.backup_id} created: {reason}'
        )
```

## Summary

The real-time backup system provides automatic data protection for critical operations without manual intervention. Combined with scheduled and manual backups, it ensures your petty cash system data is always protected and recoverable.

**Key Benefits**:
- ✅ Automatic protection for critical operations
- ✅ No manual intervention required
- ✅ Intelligent cooldown prevents performance impact
- ✅ Fast database-only backups
- ✅ Comprehensive audit trail
- ✅ Integrates with existing backup management
