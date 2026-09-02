from django.db import models


class SystemSettings(models.Model):
    """Singleton platform settings (pk=1)."""

    setup_completed = models.BooleanField(default=False)
    organization_name = models.CharField(max_length=255, blank=True, default="")
    local_id_prefix = models.CharField(max_length=16, blank=True, default="")
    login_title = models.CharField(max_length=255, blank=True, default="NovaTIP")
    login_subtitle = models.TextField(
        blank=True, default="Threat Intelligence Platform"
    )
    logo = models.ImageField(upload_to="branding/", blank=True, null=True)

    nvd_api_key = models.CharField(max_length=255, blank=True, default="")
    kev_enabled = models.BooleanField(default=True)
    bdu_enabled = models.BooleanField(default=True)
    sync_cron = models.CharField(max_length=64, blank=True, default="0 * * * *")

    email_host = models.CharField(max_length=255, blank=True, default="")
    email_port = models.PositiveIntegerField(default=587)
    email_user = models.CharField(max_length=255, blank=True, default="")
    email_password = models.CharField(max_length=255, blank=True, default="")
    email_use_tls = models.BooleanField(default=True)
    telegram_bot_token = models.CharField(max_length=255, blank=True, default="")
    telegram_chat_id = models.CharField(max_length=64, blank=True, default="")

    db_host = models.CharField(max_length=255, blank=True, default="127.0.0.1")
    db_port = models.PositiveIntegerField(default=5432)
    db_name = models.CharField(max_length=128, blank=True, default="novatip")
    db_user = models.CharField(max_length=128, blank=True, default="novatip")
    db_sslmode = models.CharField(max_length=32, blank=True, default="prefer")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "System settings"
        verbose_name_plural = "System settings"

    def __str__(self):
        state = "ready" if self.setup_completed else "setup"
        return f"Settings ({state})"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    get_solo = get_solo  # compat


class SetupProgress(models.Model):
    current_step = models.PositiveSmallIntegerField(default=1)
    completed_steps = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    get_solo = get_solo  # compat
