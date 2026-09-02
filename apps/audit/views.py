from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from .models import AuditEvent


def _is_admin(user):
    return bool(getattr(user, "is_platform_admin", False) or user.is_staff)


@login_required
@user_passes_test(_is_admin)
def audit_list(request):
    qs = AuditEvent.objects.select_related("actor").all()
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(message__icontains=q) | Q(action__icontains=q))
    page = Paginator(qs, 50).get_page(request.GET.get("page"))
    return render(
        request,
        "audit/list.html",
        {"page_obj": page, "events": page.object_list, "q": q},
    )
