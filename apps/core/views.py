from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.tickets.models import Ticket
from apps.vulns.models import Vulnerability

from .forms import SettingsForm
from .models import SystemSettings


@require_GET
def healthz(request):
    return JsonResponse({"status": "ok", "service": "novatip"})


@require_GET
def readyz(request):
    from django.db import connection

    try:
        connection.ensure_connection()
        db_ok = True
    except Exception as e:
        return JsonResponse({"status": "fail", "db": str(e)}, status=503)
    return JsonResponse({"status": "ready", "db": db_ok})


@login_required
def dashboard(request):
    qs = Vulnerability.objects.all()
    kpis = {
        "critical": qs.filter(severity="CRITICAL").count(),
        "high": qs.filter(severity="HIGH").count(),
        "kev": qs.filter(is_kev=True).count(),
        "local": qs.filter(source="LOCAL").count(),
        "total": qs.count(),
    }
    attention = qs.filter(
        Q(severity__in=["CRITICAL", "HIGH"]) | Q(is_kev=True)
    ).order_by("-published_at")[:10]
    tickets = Ticket.objects.exclude(status__in=["closed", "rejected"]).order_by("-updated_at")[:10]
    return render(
        request,
        "core/dashboard.html",
        {"kpis": kpis, "attention": attention, "tickets": tickets, "now": timezone.now()},
    )


@login_required
def settings_view(request):
    s = SystemSettings.get_solo()
    tab = request.GET.get("tab", "org")
    if request.method == "POST":
        form = SettingsForm(request.POST, request.FILES, instance=s)
        if form.is_valid():
            form.save()
            return redirect(f"{request.path}?tab={tab}")
    else:
        form = SettingsForm(instance=s)
    return render(request, "core/settings.html", {"form": form, "tab": tab, "settings_obj": s})
