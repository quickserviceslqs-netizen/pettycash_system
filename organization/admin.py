from django.contrib import admin
from .models import Company, Region, Branch, Department, CostCenter, Position

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'company')
    list_filter = ('company',)
    search_fields = ('name', 'code', 'company__name')

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'phone', 'region')
    list_filter = ('region',)
    search_fields = ('name', 'code', 'region__name')

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'company')  # company will be a method
    list_filter = ('branch',)
    search_fields = ('name', 'branch__name')

    def company(self, obj):
        return obj.branch.region.company
    company.short_description = 'Company'

@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'branch', 'company')  # add branch and company methods
    list_filter = ('department',)
    search_fields = ('name', 'department__name')

    def branch(self, obj):
        return obj.department.branch
    branch.short_description = 'Branch'

    def company(self, obj):
        return obj.department.branch.region.company
    company.short_description = 'Company'

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('title', 'department', 'branch', 'company')  # add branch and company methods
    list_filter = ('department',)
    search_fields = ('title', 'department__name')

    def branch(self, obj):
        return obj.department.branch
    branch.short_description = 'Branch'

    def company(self, obj):
        return obj.department.branch.region.company
    company.short_description = 'Company'
