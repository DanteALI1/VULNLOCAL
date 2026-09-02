from django.contrib import admin

from .models import LicenseState


@admin.register(LicenseState)
class LicenseStateAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "expires_at", "grace_until", "last_check_at", "fingerprint")
    readonly_fields = ("updated_at",)
    fieldsets = (
        (None, {"fields": ("status", "expires_at", "grace_until", "fingerprint")}),
        ("Server", {"fields": ("server_url", "last_check_at")}),
        ("Payload", {"fields": ("payload", "public_notes", "updated_at")}),
    )

    def has_add_permission(self, request):
        return not LicenseState.objects.exists()
