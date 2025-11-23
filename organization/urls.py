from django.urls import path
from . import views_bulk_import
from . import views_admin

app_name = 'organization'

urlpatterns = [
    # Cost Center Management
    path('cost-centers/', views_admin.manage_cost_centers, name='manage_cost_centers'),
    path('cost-centers/create/', views_admin.create_cost_center, name='create_cost_center'),
    path('cost-centers/<int:cost_center_id>/edit/', views_admin.edit_cost_center, name='edit_cost_center'),
    path('cost-centers/<int:cost_center_id>/delete/', views_admin.delete_cost_center, name='delete_cost_center'),
    
    # Position Management
    path('positions/', views_admin.manage_positions, name='manage_positions'),
    path('positions/create/', views_admin.create_position, name='create_position'),
    path('positions/<int:position_id>/edit/', views_admin.edit_position, name='edit_position'),
    path('positions/<int:position_id>/delete/', views_admin.delete_position, name='delete_position'),
    
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
