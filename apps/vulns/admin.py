from django.contrib import admin

from .models import LocalIdCounter, SyncCheckpoint, Vulnerability


@admin.register(Vulnerability)
class VulnerabilityAdmin(admin.ModelAdmin):
    list_display = (
        "vuln_id",
        "severity",
        "source",
        "is_kev",
        "published_at",
        "modified_at",
    )
    list_filter = ("severity", "source", "is_kev")
    search_fields = ("vuln_id", "title", "description_nvd", "description_bdu")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SyncCheckpoint)
class SyncCheckpointAdmin(admin.ModelAdmin):
    list_display = ("source", "status", "cursor", "last_success_at", "updated_at")
    search_fields = ("source", "detail")


@admin.register(LocalIdCounter)
class LocalIdCounterAdmin(admin.ModelAdmin):
    list_display = ("prefix", "year", "last_value")
    list_filter = ("year", "prefix")
