from django.db import migrations


def create_report_permissions(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    Report = apps.get_model("reports", "Report")

    ct, _ = ContentType.objects.get_or_create(app_label="reports", model="report")

    perms = [
        ("view_reports_dashboard", "Can view Reports dashboard"),
        ("view_transaction_report", "Can view Transaction report and exports"),
        ("view_treasury_report", "Can view Treasury report, drilldowns, and exports"),
        ("view_approval_report", "Can view Approval analytics and exports"),
        ("view_user_activity_report", "Can view User Activity report"),
        ("view_stuck_approvals_report", "Can view Stuck Approvals exception report"),
        (
            "view_threshold_overrides_report",
            "Can view Threshold Overrides report and exports",
        ),
        (
            "view_budget_vs_actuals_report",
            "Can view Budget vs Actuals report and exports",
        ),
    ]

    for codename, name in perms:
        Permission.objects.get_or_create(
            codename=codename, content_type=ct, defaults={"name": name}
        )


def remove_report_permissions(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    ct = ContentType.objects.filter(app_label="reports", model="report").first()
    if not ct:
        return
    codenames = [
        "view_reports_dashboard",
        "view_transaction_report",
        "view_treasury_report",
        "view_approval_report",
        "view_user_activity_report",
        "view_stuck_approvals_report",
        "view_threshold_overrides_report",
        "view_budget_vs_actuals_report",
    ]
    Permission.objects.filter(content_type=ct, codename__in=codenames).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0003_budget_allocation"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_report_permissions, remove_report_permissions),
    ]
