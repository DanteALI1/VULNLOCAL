from django.db import models


class Vulnerability(models.Model):
    class Severity(models.TextChoices):
        CRITICAL = "CRITICAL", "Critical"
        HIGH = "HIGH", "High"
        MEDIUM = "MEDIUM", "Medium"
        LOW = "LOW", "Low"
        NONE = "NONE", "None"
        UNKNOWN = "UNKNOWN", "Unknown"

    class Source(models.TextChoices):
        NVD = "NVD", "NVD"
        BDU = "BDU", "BDU"
        LOCAL = "LOCAL", "Local"
        MERGED = "MERGED", "Merged"

    vuln_id = models.CharField(max_length=64, unique=True, db_index=True)
    title = models.CharField(max_length=512, blank=True, default="")
    description_nvd = models.TextField(blank=True, default="")
    description_bdu = models.TextField(blank=True, default="")
    severity = models.CharField(
        max_length=16,
        choices=Severity.choices,
        default=Severity.UNKNOWN,
        db_index=True,
    )
    cvss_v31 = models.JSONField(null=True, blank=True)
    cvss_v30 = models.JSONField(null=True, blank=True)
    cvss_v2 = models.JSONField(null=True, blank=True)
    cvss_v4 = models.JSONField(null=True, blank=True)
    cwe = models.JSONField(default=list, blank=True)
    cpe = models.JSONField(default=list, blank=True)
    references = models.JSONField(default=list, blank=True)
    is_kev = models.BooleanField(default=False, db_index=True)
    kev_due_date = models.DateField(null=True, blank=True)
    source = models.CharField(
        max_length=16,
        choices=Source.choices,
        default=Source.NVD,
        db_index=True,
    )
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    modified_at = models.DateTimeField(null=True, blank=True)
    raw_nvd = models.JSONField(null=True, blank=True)
    raw_bdu = models.JSONField(null=True, blank=True)
    local_seq = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-id"]
        verbose_name = "Vulnerability"
        verbose_name_plural = "Vulnerabilities"
        indexes = [
            models.Index(fields=["severity", "is_kev"]),
        ]

    def __str__(self):
        return self.vuln_id

    @property
    def max_cvss_score(self):
        for blob in (self.cvss_v31, self.cvss_v30, self.cvss_v4, self.cvss_v2):
            if isinstance(blob, dict) and blob.get("score") is not None:
                try:
                    return float(blob["score"])
                except (TypeError, ValueError):
                    continue
        return None


class SyncCheckpoint(models.Model):
    class Status(models.TextChoices):
        IDLE = "idle", "Idle"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        ERROR = "error", "Error"

    source = models.CharField(max_length=32, unique=True)
    cursor = models.CharField(max_length=255, blank=True, default="")
    last_success_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.IDLE,
    )
    detail = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.source}: {self.status}"


class LocalIdCounter(models.Model):
    year = models.PositiveIntegerField()
    prefix = models.CharField(max_length=16)
    last_value = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = (("year", "prefix"),)
        verbose_name = "Local ID counter"
        verbose_name_plural = "Local ID counters"

    def __str__(self):
        return f"{self.prefix}-{self.year}-{self.last_value:04d}"
