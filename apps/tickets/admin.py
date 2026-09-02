from django.contrib import admin

from .models import Ticket, TicketEvent


class TicketEventInline(admin.TabularInline):
    model = TicketEvent
    extra = 0
    readonly_fields = ("actor", "from_status", "to_status", "action", "message", "created_at")
    can_delete = False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "title",
        "status",
        "priority",
        "assignee",
        "reporter",
        "updated_at",
    )
    list_filter = ("status", "priority")
    search_fields = ("number", "title", "vulnerability__vuln_id")
    raw_id_fields = ("vulnerability", "reporter", "assignee")
    inlines = [TicketEventInline]


@admin.register(TicketEvent)
class TicketEventAdmin(admin.ModelAdmin):
    list_display = ("ticket", "action", "from_status", "to_status", "actor", "created_at")
    list_filter = ("action",)
    search_fields = ("ticket__number", "message")
