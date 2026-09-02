from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class Ticket(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        TRIAGE = "triage", "Triage"
        IN_PROGRESS = "in_progress", "In progress"
        WAITING = "waiting", "Waiting"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"
        REJECTED = "rejected", "Rejected"

    class Priority(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    number = models.PositiveIntegerField(unique=True, db_index=True)
    title = models.CharField(max_length=512)
    description = models.TextField(blank=True, default="")
    vulnerability = models.ForeignKey(
        "vulns.Vulnerability",
        on_delete=models.PROTECT,
        related_name="tickets",
    )
    priority = models.CharField(
        max_length=16,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True,
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reported_tickets",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_tickets",
        null=True,
        blank=True,
    )
    waiting_reason = models.TextField(blank=True, default="")
    resolution_notes = models.TextField(blank=True, default="")
    reject_reason = models.TextField(blank=True, default="")
    reopen_reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"T-{self.number}: {self.title}"

    @classmethod
    def next_number(cls) -> int:
        with transaction.atomic():
            last = (
                cls.objects.select_for_update()
                .order_by("-number")
                .values_list("number", flat=True)
                .first()
            )
            return (last or 0) + 1


class TicketEvent(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_events",
    )
    from_status = models.CharField(max_length=32, blank=True, default="")
    to_status = models.CharField(max_length=32, blank=True, default="")
    action = models.CharField(max_length=64)
    message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.ticket_id}:{self.action}"
