from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .forms import TicketAssignForm, TicketCreateForm, TicketFilterForm, TicketTransitionForm
from .models import Ticket, TicketEvent
from .workflow import available_actions, can_assign, can_create, can_transition


def _notify(ticket, event: str, actor=None):
    try:
        from apps.notify.services import notify_ticket_event

        notify_ticket_event(ticket, event, actor=actor)
    except Exception:
        pass


def _audit(actor, action, message, ticket=None):
    try:
        from apps.audit.services import log_event

        kwargs = {}
        if ticket is not None:
            kwargs.update(object_type="ticket", object_id=str(ticket.pk))
        log_event(actor, action, message, **kwargs)
    except Exception:
        pass


@login_required
def ticket_list(request):
    form = TicketFilterForm(request.GET or None)
    qs = Ticket.objects.select_related("vulnerability", "reporter", "assignee")
    if form.is_valid():
        cd = form.cleaned_data
        if cd.get("q"):
            q = cd["q"].strip()
            query = (
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(vulnerability__vuln_id__icontains=q)
            )
            if q.isdigit():
                query = query | Q(number=int(q))
            qs = qs.filter(query)
        if cd.get("status"):
            qs = qs.filter(status__in=cd["status"])
        if cd.get("priority"):
            qs = qs.filter(priority=cd["priority"])
        if cd.get("assignee"):
            qs = qs.filter(assignee=cd["assignee"])
    page = Paginator(qs, 40).get_page(request.GET.get("page"))
    return render(
        request,
        "tickets/list.html",
        {
            "form": form,
            "page_obj": page,
            "tickets": page.object_list,
            "can_create": can_create(request.user),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def ticket_create(request):
    if not can_create(request.user):
        messages.error(request, "Создавать заявки могут analyst/admin.")
        return redirect("tickets:list")

    initial = {}
    vuln_id = request.GET.get("vuln")
    if vuln_id:
        initial["vulnerability"] = vuln_id

    if request.method == "POST":
        form = TicketCreateForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                ticket = form.save(commit=False)
                ticket.number = Ticket.next_number()
                ticket.reporter = request.user
                ticket.status = Ticket.Status.NEW
                assignee = form.cleaned_data.get("assignee")
                if assignee:
                    if not can_assign(request.user, assignee):
                        messages.error(request, "Исполнитель должен иметь роль ticket_assignee.")
                        return render(request, "tickets/create.html", {"form": form})
                    ticket.assignee = assignee
                    ticket.status = Ticket.Status.TRIAGE
                ticket.save()
                TicketEvent.objects.create(
                    ticket=ticket,
                    actor=request.user,
                    from_status="",
                    to_status=ticket.status,
                    action="created",
                    message=f"Создана заявка T-{ticket.number}",
                )
            _notify(ticket, "created", actor=request.user)
            _audit(request.user, "ticket.created", f"T-{ticket.number}", ticket=ticket)
            messages.success(request, f"Создана заявка T-{ticket.number}")
            return redirect("tickets:detail", pk=ticket.pk)
    else:
        form = TicketCreateForm(initial=initial)
    return render(request, "tickets/create.html", {"form": form})


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(
        Ticket.objects.select_related("vulnerability", "reporter", "assignee"),
        pk=pk,
    )
    events = ticket.events.select_related("actor").all()
    return render(
        request,
        "tickets/detail.html",
        {
            "ticket": ticket,
            "events": events,
            "actions": available_actions(request.user, ticket),
            "assign_form": TicketAssignForm(),
            "transition_form": TicketTransitionForm(),
            "can_assign": can_create(request.user),
        },
    )


@login_required
@require_POST
def ticket_assign(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    form = TicketAssignForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Некорректные данные назначения.")
        return redirect("tickets:detail", pk=pk)
    assignee = form.cleaned_data["assignee"]
    if not can_assign(request.user, assignee):
        messages.error(request, "Назначать может analyst/admin на роль ticket_assignee.")
        return redirect("tickets:detail", pk=pk)

    old = ticket.status
    ticket.assignee = assignee
    if ticket.status == Ticket.Status.NEW:
        ticket.status = Ticket.Status.TRIAGE
    ticket.save()
    TicketEvent.objects.create(
        ticket=ticket,
        actor=request.user,
        from_status=old,
        to_status=ticket.status,
        action="assigned",
        message=f"Назначен {assignee.display_name()}",
    )
    _notify(ticket, "assigned", actor=request.user)
    _audit(request.user, "ticket.assigned", f"T-{ticket.number} → {assignee}", ticket=ticket)
    messages.success(request, "Исполнитель назначен.")
    return redirect("tickets:detail", pk=pk)


@login_required
@require_POST
def ticket_transition(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    form = TicketTransitionForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Некорректные данные перехода.")
        return redirect("tickets:detail", pk=pk)

    cd = form.cleaned_data
    new_status = cd["new_status"]
    force = bool(cd.get("force"))

    # Apply reason fields onto ticket before permission check
    if cd.get("waiting_reason"):
        ticket.waiting_reason = cd["waiting_reason"]
    if cd.get("resolution_notes"):
        ticket.resolution_notes = cd["resolution_notes"]
    if cd.get("reject_reason"):
        ticket.reject_reason = cd["reject_reason"]
    if cd.get("reopen_reason"):
        ticket.reopen_reason = cd["reopen_reason"]

    if (
        ticket.status == Ticket.Status.RESOLVED
        and new_status == Ticket.Status.CLOSED
        and not force
        and not cd.get("confirm_close")
    ):
        messages.error(request, "Подтвердите закрытие заявки.")
        return redirect("tickets:detail", pk=pk)

    ok, reason = can_transition(request.user, ticket, new_status, force=force)
    if not ok:
        messages.error(request, reason)
        return redirect("tickets:detail", pk=pk)

    old = ticket.status
    ticket.status = new_status
    ticket.save()

    msg = f"{old} → {new_status}"
    if force and cd.get("force_reason"):
        msg += f" (force: {cd['force_reason']})"
    TicketEvent.objects.create(
        ticket=ticket,
        actor=request.user,
        from_status=old,
        to_status=new_status,
        action="force_close" if force else "transition",
        message=msg,
    )
    _notify(ticket, "force_close" if force else "transition", actor=request.user)
    _audit(
        request.user,
        "ticket.force_close" if force else "ticket.transition",
        f"T-{ticket.number}: {msg}",
        ticket=ticket,
    )
    messages.success(request, f"Статус обновлён: {ticket.get_status_display()}")
    return redirect("tickets:detail", pk=pk)
