from django.db import models
from django.utils import timezone


class LicenseState(models.Model):
    """Singleton license client state (pk=1)."""

    class Status(models.TextChoices):
        VALID = "valid", "Valid"
        GRACE = "grace", "Grace"
        INVALID = "invalid", "Invalid"
        MISSING = "missing", "Missing"

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.MISSING,
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    grace_until = models.DateTimeField(null=True, blank=True)
    fingerprint = models.CharField(max_length=128, blank=True, default="")
    server_url = models.URLField(blank=True, default="")
    last_check_at = models.DateTimeField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    public_notes = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "License state"
        verbose_name_plural = "License state"

    def __str__(self):
        return f"License ({self.status})"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def refresh_status_from_dates(self):
        """Derive status from expires_at / grace_until without network."""
        now = timezone.now()
        if not self.payload and self.status == self.Status.MISSING:
            return self.status
        if self.expires_at and self.expires_at > now:
            self.status = self.Status.VALID
        elif self.grace_until and self.grace_until > now:
            self.status = self.Status.GRACE
        elif self.payload or self.expires_at or self.grace_until:
            self.status = self.Status.INVALID
        else:
            self.status = self.Status.MISSING
        return self.status
