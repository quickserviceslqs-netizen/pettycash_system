"""
Bulk Import for Organization Entities
Handles CSV uploads for Companies, Regions, Branches, Departments, Cost Centers, Positions
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import HttpResponse
from django.db import transaction
import csv
import io
from organization.models import Company, Region, Branch, Department, CostCenter, Position
from settings_manager.views import log_activity


# ============================================
# COMPANIES
# ============================================

@login_required
@permission_required('organization.add_company', raise_exception=True)
def download_companies_template(request):
    """Download CSV template for bulk company import"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="companies_import_template.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['name', 'code'])
    writer.writerow(['Quick Services LQS', 'QSLQS'])
    writer.writerow(['ABC Corporation', 'ABC'])
    writer.writerow(['XYZ Limited', 'XYZ'])
    writer.writerow([])
    writer.writerow(['INSTRUCTIONS:'])
    writer.writerow(['- name: Company name (must be unique)'])
    writer.writerow(['- code: Short code (2-10 characters, must be unique)'])
    writer.writerow(['- Delete example rows before uploading'])
    
    return response


@login_required
@permission_required('organization.add_company', raise_exception=True)
def import_companies(request):
    """Bulk import companies from CSV"""
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file')
            return redirect('import_organizations')
        
        try:
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            success_count = 0
            error_count = 0
            errors = []
            
            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):
                    try:
                        if not row.get('name') or row['name'].startswith('INSTRUCTIONS'):
                            continue
                        
                        name = row['name'].strip()
                        code = row['code'].strip()
                        
                        if not name or not code:
                            errors.append(f"Row {row_num}: Missing name or code")
                            error_count += 1
                            continue
                        
                        if Company.objects.filter(name__iexact=name).exists():
                            errors.append(f"Row {row_num}: Company '{name}' already exists")
                            error_count += 1
                            continue
                        
                        if Company.objects.filter(code__iexact=code).exists():
                            errors.append(f"Row {row_num}: Code '{code}' already exists")
                            error_count += 1
                            continue
                        
                        Company.objects.create(name=name, code=code)
                        success_count += 1
                        
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
                        error_count += 1
            
            if success_count > 0:
                messages.success(request, f'✅ Successfully imported {success_count} compan{"y" if success_count == 1 else "ies"}')
                log_activity(request.user, 'ORG_BULK_IMPORT', f'Imported {success_count} companies')
            
            if error_count > 0:
                messages.warning(request, f'⚠️ {error_count} row(s) failed')
                for error in errors[:10]:
                    messages.error(request, error)
            
            return redirect('import_organizations')
            
        except Exception as e:
            messages.error(request, f'Error processing CSV: {str(e)}')
            return redirect('import_organizations')
    
    return redirect('import_organizations')


# ============================================
# REGIONS
# ============================================

@login_required
@permission_required('organization.add_region', raise_exception=True)
def download_regions_template(request):
    """Download CSV template for bulk region import"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="regions_import_template.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['name', 'code', 'company_name'])
    
    # Get example companies
    companies = Company.objects.all()[:3]
    if companies:
        for company in companies:
            writer.writerow([f'{company.name} - East Africa', f'{company.code}EA', company.name])
    else:
        writer.writerow(['East Africa', 'EA', 'Quick Services LQS'])
        writer.writerow(['West Africa', 'WA', 'Quick Services LQS'])
    
    writer.writerow([])
    writer.writerow(['INSTRUCTIONS:'])
    writer.writerow(['- name: Region name'])
    writer.writerow(['- code: Short code (2-10 characters, must be unique)'])
    writer.writerow(['- company_name: Must exactly match existing company name'])
    writer.writerow([])
    writer.writerow(['AVAILABLE COMPANIES:'])
    for company in Company.objects.all():
        writer.writerow([f'  → {company.name}'])
    
    return response


@login_required
@permission_required('organization.add_region', raise_exception=True)
def import_regions(request):
    """Bulk import regions from CSV"""
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file')
            return redirect('import_organizations')
        
        try:
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            success_count = 0
            error_count = 0
            errors = []
            
            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):
                    try:
                        if not row.get('name') or row['name'].startswith('INSTRUCTIONS'):
                            continue
                        
                        name = row['name'].strip()
                        code = row['code'].strip()
                        company_name = row['company_name'].strip()
                        
                        if not all([name, code, company_name]):
                            errors.append(f"Row {row_num}: Missing required fields")
                            error_count += 1
                            continue
                        
                        try:
                            company = Company.objects.get(name__iexact=company_name)
                        except Company.DoesNotExist:
                            errors.append(f"Row {row_num}: Company '{company_name}' not found")
                            error_count += 1
                            continue
                        
                        if Region.objects.filter(code__iexact=code).exists():
                            errors.append(f"Row {row_num}: Code '{code}' already exists")
                            error_count += 1
                            continue
                        
                        Region.objects.create(name=name, code=code, company=company)
                        success_count += 1
                        
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
                        error_count += 1
            
            if success_count > 0:
                messages.success(request, f'✅ Successfully imported {success_count} region(s)')
                log_activity(request.user, 'ORG_BULK_IMPORT', f'Imported {success_count} regions')
            
            if error_count > 0:
                messages.warning(request, f'⚠️ {error_count} row(s) failed')
                for error in errors[:10]:
                    messages.error(request, error)
            
            return redirect('import_organizations')
            
        except Exception as e:
            messages.error(request, f'Error processing CSV: {str(e)}')
            return redirect('import_organizations')
    
    return redirect('import_organizations')


# ============================================
# BRANCHES
# ============================================

@login_required
@permission_required('organization.add_branch', raise_exception=True)
def download_branches_template(request):
    """Download CSV template for bulk branch import"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="branches_import_template.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['name', 'code', 'phone', 'region_name', 'company_name'])
    
    # Get example data
    regions = Region.objects.select_related('company').all()[:3]
    if regions:
        for region in regions:
            writer.writerow([
                f'{region.name} Branch',
                f'{region.code}BR',
                '+254700000000',
                region.name,
                region.company.name
            ])
    else:
        writer.writerow(['Nairobi Branch', 'NBIBR', '+254700000000', 'East Africa', 'Quick Services LQS'])
        writer.writerow(['Mombasa Branch', 'MSABR', '+254710000000', 'East Africa', 'Quick Services LQS'])
    
    writer.writerow([])
    writer.writerow(['INSTRUCTIONS:'])
    writer.writerow(['- name: Branch name (must be unique)'])
    writer.writerow(['- code: Short code (2-10 characters, must be unique)'])
    writer.writerow(['- phone: Contact phone number (optional)'])
    writer.writerow(['- region_name: Must exactly match existing region'])
    writer.writerow(['- company_name: Must exactly match existing company'])
    writer.writerow([])
    writer.writerow(['AVAILABLE REGIONS:'])
    for region in Region.objects.select_related('company').all():
        writer.writerow([f'  → {region.name} ({region.company.name})'])
    
    return response


@login_required
@permission_required('organization.add_branch', raise_exception=True)
def import_branches(request):
    """Bulk import branches from CSV"""
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file')
            return redirect('import_organizations')
        
        try:
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            success_count = 0
            error_count = 0
            errors = []
            
            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):
                    try:
                        if not row.get('name') or row['name'].startswith('INSTRUCTIONS'):
                            continue
                        
                        name = row['name'].strip()
                        code = row['code'].strip()
                        phone = row.get('phone', '').strip()
                        region_name = row['region_name'].strip()
                        company_name = row['company_name'].strip()
                        
                        if not all([name, code, region_name, company_name]):
                            errors.append(f"Row {row_num}: Missing required fields")
                            error_count += 1
                            continue
                        
                        try:
                            company = Company.objects.get(name__iexact=company_name)
                        except Company.DoesNotExist:
                            errors.append(f"Row {row_num}: Company '{company_name}' not found")
                            error_count += 1
                            continue
                        
                        try:
                            region = Region.objects.get(name__iexact=region_name, company=company)
                        except Region.DoesNotExist:
                            errors.append(f"Row {row_num}: Region '{region_name}' not found for company '{company_name}'")
                            error_count += 1
                            continue
                        
                        if Branch.objects.filter(name__iexact=name).exists():
                            errors.append(f"Row {row_num}: Branch '{name}' already exists")
                            error_count += 1
                            continue
                        
                        if Branch.objects.filter(code__iexact=code).exists():
                            errors.append(f"Row {row_num}: Code '{code}' already exists")
                            error_count += 1
                            continue
                        
                        Branch.objects.create(
                            name=name,
                            code=code,
                            phone=phone if phone else None,
                            region=region
                        )
                        success_count += 1
                        
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
                        error_count += 1
            
            if success_count > 0:
                messages.success(request, f'✅ Successfully imported {success_count} branch(es)')
                log_activity(request.user, 'ORG_BULK_IMPORT', f'Imported {success_count} branches')
            
            if error_count > 0:
                messages.warning(request, f'⚠️ {error_count} row(s) failed')
                for error in errors[:10]:
                    messages.error(request, error)
            
            return redirect('import_organizations')
            
        except Exception as e:
            messages.error(request, f'Error processing CSV: {str(e)}')
            return redirect('import_organizations')
    
    return redirect('import_organizations')


# ============================================
# DEPARTMENTS
# ============================================

@login_required
@permission_required('organization.add_department', raise_exception=True)
def download_departments_template(request):
    """Download CSV template for bulk department import"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="departments_import_template.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['name', 'branch_name'])
    
    # Get example branches
    branches = Branch.objects.all()[:3]
    dept_names = ['Finance', 'Operations', 'IT', 'Marketing', 'HR']
    
    if branches:
        for i, branch in enumerate(branches):
            writer.writerow([dept_names[i % len(dept_names)], branch.name])
    else:
        writer.writerow(['Finance', 'Nairobi Branch'])
        writer.writerow(['Operations', 'Nairobi Branch'])
        writer.writerow(['IT', 'Mombasa Branch'])
    
    writer.writerow([])
    writer.writerow(['INSTRUCTIONS:'])
    writer.writerow(['- name: Department name'])
    writer.writerow(['- branch_name: Must exactly match existing branch'])
    writer.writerow(['- Same department name can exist in multiple branches'])
    writer.writerow([])
    writer.writerow(['AVAILABLE BRANCHES:'])
    for branch in Branch.objects.select_related('region__company').all():
        writer.writerow([f'  → {branch.name} ({branch.region.name}, {branch.region.company.name})'])
    
    return response


@login_required
@permission_required('organization.add_department', raise_exception=True)
def import_departments(request):
    """Bulk import departments from CSV"""
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file')
            return redirect('import_organizations')
        
        try:
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            success_count = 0
            error_count = 0
            errors = []
            
            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):
                    try:
                        if not row.get('name') or row['name'].startswith('INSTRUCTIONS'):
                            continue
                        
                        name = row['name'].strip()
                        branch_name = row['branch_name'].strip()
                        
                        if not all([name, branch_name]):
                            errors.append(f"Row {row_num}: Missing required fields")
                            error_count += 1
                            continue
                        
                        try:
                            branch = Branch.objects.get(name__iexact=branch_name)
                        except Branch.DoesNotExist:
                            errors.append(f"Row {row_num}: Branch '{branch_name}' not found")
                            error_count += 1
                            continue
                        
                        if Department.objects.filter(name__iexact=name, branch=branch).exists():
                            errors.append(f"Row {row_num}: Department '{name}' already exists in branch '{branch_name}'")
                            error_count += 1
                            continue
                        
                        Department.objects.create(name=name, branch=branch)
                        success_count += 1
                        
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
                        error_count += 1
            
            if success_count > 0:
                messages.success(request, f'✅ Successfully imported {success_count} department(s)')
                log_activity(request.user, 'ORG_BULK_IMPORT', f'Imported {success_count} departments')
            
            if error_count > 0:
                messages.warning(request, f'⚠️ {error_count} row(s) failed')
                for error in errors[:10]:
                    messages.error(request, error)
            
            return redirect('import_organizations')
            
        except Exception as e:
            messages.error(request, f'Error processing CSV: {str(e)}')
            return redirect('import_organizations')
    
    return redirect('import_organizations')


# ============================================
# MAIN IMPORT PAGE
# ============================================

@login_required
def import_organizations(request):
    """Main page for bulk importing all organization entities"""
    context = {
        'companies_count': Company.objects.count(),
        'regions_count': Region.objects.count(),
        'branches_count': Branch.objects.count(),
        'departments_count': Department.objects.count(),
    }
    return render(request, 'organization/bulk_import.html', context)
