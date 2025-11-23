from django.urls import path
from . import views_bulk_import

app_name = 'organization'

urlpatterns = [
    # Main bulk import page
    path('bulk-import/', views_bulk_import.import_organizations, name='import_organizations'),
    
    # Companies
    path('bulk-import/companies/template/', views_bulk_import.download_companies_template, name='download_companies_template'),
    path('bulk-import/companies/import/', views_bulk_import.import_companies, name='import_companies'),
    
    # Regions
    path('bulk-import/regions/template/', views_bulk_import.download_regions_template, name='download_regions_template'),
    path('bulk-import/regions/import/', views_bulk_import.import_regions, name='import_regions'),
    
    # Branches
    path('bulk-import/branches/template/', views_bulk_import.download_branches_template, name='download_branches_template'),
    path('bulk-import/branches/import/', views_bulk_import.import_branches, name='import_branches'),
    
    # Departments
    path('bulk-import/departments/template/', views_bulk_import.download_departments_template, name='download_departments_template'),
    path('bulk-import/departments/import/', views_bulk_import.import_departments, name='import_departments'),
]
