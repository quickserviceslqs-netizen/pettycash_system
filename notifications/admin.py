from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("to_email", "subject", "status", "sent_at", "created_at")
    list_filter = ("status",)
    search_fields = ("to_email", "subject")
