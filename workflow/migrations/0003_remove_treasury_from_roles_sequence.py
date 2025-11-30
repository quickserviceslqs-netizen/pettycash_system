from django.db import migrations


def remove_treasury_forward(apps, schema_editor):
    ApprovalThreshold = apps.get_model('workflow', 'ApprovalThreshold')
    changed = 0
    for thr in ApprovalThreshold.objects.all():
        try:
            roles = thr.roles_sequence or []
        except Exception:
            roles = []

        # Normalize and filter out 'treasury' entries (case-insensitive)
        new_roles = [r for r in roles if str(r).strip().lower() != 'treasury']
        if new_roles != roles:
            thr.roles_sequence = new_roles
            thr.save(update_fields=['roles_sequence'])
            changed += 1


def remove_treasury_reverse(apps, schema_editor):
    # Reverse migration is a no-op because we intentionally remove the treasury role
    # from stored thresholds to align DB with application logic.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('workflow', '0003_approvalthreshold_requires_ceo'),
    ]

    operations = [
        migrations.RunPython(remove_treasury_forward, remove_treasury_reverse),
    ]
