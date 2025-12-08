from django.db import migrations


def seed_apps(apps, schema_editor):
    App = apps.get_model('accounts', 'App')
    defaults = {
        'transactions': {'display_name': 'Transactions', 'url': '/transactions/'},
        'treasury': {'display_name': 'Treasury', 'url': '/treasury/'},
        'workflow': {'display_name': 'Workflow', 'url': '/workflow/'},
        'reports': {'display_name': 'Reports', 'url': '/reports/dashboard/'},
    }
    for name, data in defaults.items():
        App.objects.get_or_create(name=name, defaults=data)


def remove_apps(apps, schema_editor):
    App = apps.get_model('accounts', 'App')
    App.objects.filter(name__in=['transactions', 'treasury', 'workflow', 'reports']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_user_security_fields'),
    ]

    operations = [
        migrations.RunPython(seed_apps, remove_apps),
    ]
