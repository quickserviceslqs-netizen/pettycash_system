from django.contrib import admin
from .models import ApprovalThreshold

@admin.register(ApprovalThreshold)
class ApprovalThresholdAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'origin_type', 'min_amount', 'max_amount',
        'allow_urgent_fasttrack', 'requires_cfo', 'is_active'
    )
    list_filter = ('origin_type', 'is_active', 'allow_urgent_fasttrack')
    search_fields = ('name',)
