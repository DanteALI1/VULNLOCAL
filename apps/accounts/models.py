from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        PLATFORM_ADMIN = "platform_admin", "Platform Admin"
        ANALYST = "analyst", "Analyst"
        TICKET_ASSIGNEE = "ticket_assignee", "Ticket Assignee"
        VERIFIER = "verifier", "Verifier"

    role = models.CharField(max_length=32, choices=Role.choices, default=Role.ANALYST)
    full_name = models.CharField(max_length=255, blank=True)
    is_verifier = models.BooleanField(default=False)

    def display_name(self):
        return self.full_name or self.get_full_name() or self.username

    @property
    def is_platform_admin(self):
        return self.role == self.Role.PLATFORM_ADMIN or self.is_superuser

    def can_manage_tickets(self):
        return self.role in {
            self.Role.PLATFORM_ADMIN,
            self.Role.ANALYST,
            self.Role.TICKET_ASSIGNEE,
            self.Role.VERIFIER,
        } or self.is_verifier
