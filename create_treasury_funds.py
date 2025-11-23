import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
django.setup()

from organization.models import Company, Region, Branch
from treasury.models import TreasuryFund
from decimal import Decimal

# First, check if we have organization structure
companies = Company.objects.all()
if not companies.exists():
    print("Creating test organization structure...")
    
    # Create a test company
    company = Company.objects.create(
        name="Test Company Ltd",
        code="TEST001"
    )
    
    # Create a test region
    region = Region.objects.create(
        name="Central Region",
        code="CR001",
        company=company
    )
    
    # Create a test branch
    branch = Branch.objects.create(
        name="Main Branch",
        code="MB001",
        region=region,
        company=company
    )
    
    print(f"✓ Created: {company.name}")
    print(f"✓ Created: {region.name}")
    print(f"✓ Created: {branch.name}")
else:
    company = companies.first()
    regions = Region.objects.filter(company=company)
    branches = Branch.objects.filter(region__company=company)
    region = regions.first() if regions.exists() else None
    branch = branches.first() if branches.exists() else None
    print(f"Using existing: {company.name}")

# Create treasury funds
existing_funds = TreasuryFund.objects.filter(company=company).count()
if existing_funds > 0:
    print(f"\nℹ️  {existing_funds} treasury funds already exist")
else:
    print("\nCreating treasury funds...")
    
    # Company-level fund
    fund1 = TreasuryFund.objects.create(
        company=company,
        current_balance=Decimal('100000.00'),
        reorder_level=Decimal('20000.00')
    )
    print(f"✓ Created company fund: {fund1.fund_id} - Balance: {fund1.current_balance}")
    
    # Region-level fund
    if region:
        fund2 = TreasuryFund.objects.create(
            company=company,
            region=region,
            current_balance=Decimal('50000.00'),
            reorder_level=Decimal('10000.00')
        )
        print(f"✓ Created region fund: {fund2.fund_id} - Balance: {fund2.current_balance}")
    
    # Branch-level fund
    if branch:
        fund3 = TreasuryFund.objects.create(
            company=company,
            region=region,
            branch=branch,
            current_balance=Decimal('25000.00'),
            reorder_level=Decimal('5000.00')
        )
        print(f"✓ Created branch fund: {fund3.fund_id} - Balance: {fund3.current_balance}")

# Summary
total_funds = TreasuryFund.objects.count()
print(f"\n✅ Total Treasury Funds: {total_funds}")
for fund in TreasuryFund.objects.all():
    location = f"{fund.company.name}"
    if fund.region:
        location += f" > {fund.region.name}"
    if fund.branch:
        location += f" > {fund.branch.name}"
    print(f"   {fund.fund_id}: {location} - Balance: {fund.current_balance}")
