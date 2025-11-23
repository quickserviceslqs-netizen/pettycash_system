"""
Bulk User Import via CSV Template
Allows admins to upload multiple user invitations at once
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
import csv
import io
from accounts.models import User
from accounts.models_device import UserInvitation
from organization.models import Company, Department, Branch
from settings_manager.models import get_setting
from settings_manager.views import log_activity


@login_required
@permission_required('accounts.add_userinvitation', raise_exception=True)
def download_template(request):
    """
    Download CSV template for bulk user import
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="user_import_template.csv"'
    
    writer = csv.writer(response)
    
    # Write header row with instructions
    writer.writerow([
        'email', 'first_name', 'last_name', 'role', 
        'company_name', 'department_name', 'branch_name', 
        'assigned_apps'
    ])
    
    # Write example rows
    writer.writerow([
        'john.doe@example.com',
        'John',
        'Doe',
        'REQUESTER',
        'Quick Services LQS',
        'Finance',
        'Head Office',
        'treasury,workflow'  # Comma-separated app names
    ])
    writer.writerow([
        'jane.smith@example.com',
        'Jane',
        'Smith',
        'APPROVER',
        'Quick Services LQS',
        'Finance',
        'Head Office',
        'treasury,workflow,reports'
    ])
    
    # Add instructions as comments
    writer.writerow([])
    writer.writerow(['INSTRUCTIONS:'])
    writer.writerow(['- Delete the example rows above before uploading'])
    writer.writerow(['- email: Must be valid and unique'])
    writer.writerow(['- first_name, last_name: User\'s full name'])
    writer.writerow(['- role: REQUESTER, APPROVER, FINANCE, or ADMIN'])
    writer.writerow(['- company_name, department_name, branch_name: Must exist in system'])
    writer.writerow(['- assigned_apps: Comma-separated app names (treasury, workflow, reports, etc.)'])
    writer.writerow(['- Username will be auto-generated as FirstnameLast name (e.g., JohnDoe)'])
    writer.writerow(['- User will receive invitation email to set their password'])
    
    return response


@login_required
@permission_required('accounts.add_userinvitation', raise_exception=True)
def bulk_import(request):
    """
    Upload and process CSV file for bulk user invitations
    """
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        
        # Validate file type
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file')
            return redirect('bulk_import')
        
        # Read and decode file
        try:
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            success_count = 0
            error_count = 0
            errors = []
            
            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (after header)
                    try:
                        # Skip empty rows or instruction rows
                        if not row.get('email') or row['email'].startswith('INSTRUCTIONS'):
                            continue
                        
                        # Validate required fields
                        email = row['email'].strip()
                        first_name = row['first_name'].strip()
                        last_name = row['last_name'].strip()
                        role = row['role'].strip().upper()
                        
                        if not all([email, first_name, last_name, role]):
                            errors.append(f"Row {row_num}: Missing required fields")
                            error_count += 1
                            continue
                        
                        # Validate role
                        valid_roles = [choice[0] for choice in User.ROLE_CHOICES]
                        if role not in valid_roles:
                            errors.append(f"Row {row_num}: Invalid role '{role}'. Must be one of: {', '.join(valid_roles)}")
                            error_count += 1
                            continue
                        
                        # Check if user or invitation already exists
                        if User.objects.filter(email=email).exists():
                            errors.append(f"Row {row_num}: User with email {email} already exists")
                            error_count += 1
                            continue
                        
                        if UserInvitation.objects.filter(email=email, status='pending').exists():
                            errors.append(f"Row {row_num}: Pending invitation already exists for {email}")
                            error_count += 1
                            continue
                        
                        # Get organizational entities
                        company = None
                        department = None
                        branch = None
                        
                        if row.get('company_name'):
                            try:
                                company = Company.objects.get(name=row['company_name'].strip())
                            except Company.DoesNotExist:
                                errors.append(f"Row {row_num}: Company '{row['company_name']}' not found")
                                error_count += 1
                                continue
                        
                        if row.get('department_name'):
                            try:
                                department = Department.objects.get(name=row['department_name'].strip())
                            except Department.DoesNotExist:
                                errors.append(f"Row {row_num}: Department '{row['department_name']}' not found")
                                error_count += 1
                                continue
                        
                        if row.get('branch_name'):
                            try:
                                branch = Branch.objects.get(name=row['branch_name'].strip())
                            except Branch.DoesNotExist:
                                errors.append(f"Row {row_num}: Branch '{row['branch_name']}' not found")
                                error_count += 1
                                continue
                        
                        # Parse assigned apps
                        assigned_apps_list = []
                        if row.get('assigned_apps'):
                            app_names = [app.strip() for app in row['assigned_apps'].split(',')]
                            assigned_apps_list = app_names
                        
                        # Get invitation expiry
                        expiry_days = int(get_setting('INVITATION_EXPIRY_DAYS', '7'))
                        expires_at = timezone.now() + timedelta(days=expiry_days)
                        
                        # Create invitation
                        invitation = UserInvitation.objects.create(
                            email=email,
                            first_name=first_name,
                            last_name=last_name,
                            role=role,
                            company=company,
                            department=department,
                            branch=branch,
                            invited_by=request.user,
                            expires_at=expires_at,
                            assigned_apps=assigned_apps_list
                        )
                        
                        # Send invitation email
                        try:
                            invitation_url = request.build_absolute_uri(
                                f'/accounts/signup/{invitation.token}/'
                            )
                            
                            send_mail(
                                subject=f'Invitation to join {company.name if company else "the system"}',
                                message=f'''
Hello {first_name},

You've been invited to join as a {invitation.get_role_display()}.

Click here to complete your registration:
{invitation_url}

Your username will be auto-generated as: {first_name}{last_name}
You will set your password during registration.

This invitation expires on {expires_at.strftime("%B %d, %Y at %I:%M %p")}.

Best regards,
{request.user.get_full_name() or request.user.username}
                                ''',
                                from_email=settings.DEFAULT_FROM_EMAIL,
                                recipient_list=[email],
                                fail_silently=False,
                            )
                        except Exception as e:
                            errors.append(f"Row {row_num}: Email sent failed for {email}: {str(e)}")
                        
                        success_count += 1
                        
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
                        error_count += 1
            
            # Show results
            if success_count > 0:
                messages.success(
                    request, 
                    f'✅ Successfully created {success_count} invitation(s)'
                )
                log_activity(
                    request.user,
                    'USER_BULK_IMPORT',
                    f'Bulk imported {success_count} user invitations'
                )
            
            if error_count > 0:
                messages.warning(
                    request,
                    f'⚠️ {error_count} row(s) failed. See details below.'
                )
                for error in errors[:10]:  # Show first 10 errors
                    messages.error(request, error)
                
                if len(errors) > 10:
                    messages.info(request, f'... and {len(errors) - 10} more errors')
            
            return redirect('manage_invitations')
            
        except Exception as e:
            messages.error(request, f'Error processing CSV file: {str(e)}')
            return redirect('bulk_import')
    
    # GET request - show upload form
    context = {
        'companies': Company.objects.all(),
        'departments': Department.objects.all(),
        'branches': Branch.objects.all(),
        'roles': User.ROLE_CHOICES,
    }
    return render(request, 'accounts/bulk_import.html', context)
