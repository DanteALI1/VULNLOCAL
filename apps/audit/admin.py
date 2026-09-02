from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "actor", "object_type", "object_id", "ip")
    list_filter = ("action", "object_type")
    search_fields = ("message", "object_id", "action")
    readonly_fields = ("created_at",)
