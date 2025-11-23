import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
django.setup()

from django.db import connection

# Drop all treasury tables
with connection.cursor() as cursor:
    print("Dropping treasury tables...")
    tables = [
        'treasury_fundforecast',
        'treasury_paymenttracking',
        'treasury_alert',
        'treasury_dashboardmetric',
        'treasury_treasurydashboard',
        'treasury_varianceadjustment',
        'treasury_ledgerentry',
        'treasury_replenishmentrequest',
        'treasury_paymentexecution',
        'treasury_payment',
        'treasury_treasuryfund',
    ]
    
    for table in tables:
        try:
            cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
            print(f'✓ Dropped {table}')
        except Exception as e:
            print(f'  Skip {table}: {str(e)[:50]}')
    
print("\n✅ Treasury tables dropped. Now run: python manage.py migrate treasury")
