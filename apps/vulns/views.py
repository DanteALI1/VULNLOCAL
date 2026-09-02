from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import LocalVulnForm, VulnFilterForm
from .models import Vulnerability
from .services import allocate_local_id


@login_required
def vuln_list(request):
    form = VulnFilterForm(request.GET or None)
    qs = Vulnerability.objects.all()
    chips = []
    if form.is_valid():
        cd = form.cleaned_data
        chips = form.active_chips()
        if cd.get("q"):
            q = cd["q"].strip()
            qs = qs.filter(
                Q(vuln_id__icontains=q)
                | Q(title__icontains=q)
                | Q(description_nvd__icontains=q)
                | Q(description_bdu__icontains=q)
            )
        if cd.get("severity"):
            qs = qs.filter(severity__in=cd["severity"])
        if cd.get("is_kev"):
            qs = qs.filter(is_kev=True)
        if cd.get("source"):
            qs = qs.filter(source=cd["source"])
        if cd.get("cwe"):
            qs = qs.filter(cwe__icontains=cd["cwe"].strip())
    else:
        chips = form.active_chips()

    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "vulns/list.html",
        {
            "form": form,
            "page_obj": page,
            "vulnerabilities": page.object_list,
            "chips": chips,
            "total_count": paginator.count,
        },
    )


@login_required
def vuln_detail(request, pk):
    vuln = get_object_or_404(Vulnerability, pk=pk)
    related_tickets = []
    try:
        related_tickets = list(vuln.tickets.select_related("assignee", "reporter").all()[:20])
    except Exception:
        related_tickets = []

    cvss_tabs = [
        {"key": "v31", "label": "3.1", "data": vuln.cvss_v31},
        {"key": "v30", "label": "3.0", "data": vuln.cvss_v30},
        {"key": "v2", "label": "2.0", "data": vuln.cvss_v2},
        {"key": "v4", "label": "4.0", "data": vuln.cvss_v4},
    ]
    active_cvss = next((t for t in cvss_tabs if t["data"]), cvss_tabs[0])

    return render(
        request,
        "vulns/detail.html",
        {
            "vuln": vuln,
            "related_tickets": related_tickets,
            "cvss_tabs": cvss_tabs,
            "active_cvss_key": active_cvss["key"],
            "desc_default": "bdu" if vuln.description_bdu and not vuln.description_nvd else "nvd",
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def vuln_create_local(request):
    from apps.accounts.models import User

    if not (
        request.user.is_platform_admin
        or getattr(request.user, "role", None) == User.Role.ANALYST
    ):
        messages.error(request, "Недостаточно прав для создания локальной уязвимости.")
        return redirect("vulns:list")

    if request.method == "POST":
        form = LocalVulnForm(request.POST)
        if form.is_valid():
            try:
                vuln_id = allocate_local_id()
            except ValueError as exc:
                messages.error(request, str(exc))
                return render(request, "vulns/create_local.html", {"form": form})
            obj = form.save(commit=False)
            obj.vuln_id = vuln_id
            obj.source = Vulnerability.Source.LOCAL
            try:
                obj.local_seq = int(vuln_id.rsplit("-", 1)[-1])
            except ValueError:
                obj.local_seq = None
            if not obj.description_nvd and obj.title:
                obj.description_nvd = obj.title
            obj.save()
            messages.success(request, f"Создана локальная карточка {obj.vuln_id}")
            return redirect("vulns:detail", pk=obj.pk)
    else:
        form = LocalVulnForm()
    return render(request, "vulns/create_local.html", {"form": form})
