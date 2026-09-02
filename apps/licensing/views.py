from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .models import LicenseState
from .services import (
    check_license,
    install_dev_grace_license,
    install_license_file,
    machine_fingerprint,
)


class LicenseUploadForm(forms.Form):
    license_file = forms.FileField(
        label="Файл лицензии (.novalic)",
        required=True,
        help_text="JSON с полями org, seats, expires, signature",
    )


@login_required
@require_http_methods(["GET", "POST"])
def license_status(request):
    state = LicenseState.get_solo()
    if not state.fingerprint:
        state.fingerprint = machine_fingerprint()
        state.save(update_fields=["fingerprint", "updated_at"])

    form = LicenseUploadForm()
    if request.method == "POST":
        action = request.POST.get("action", "upload")
        if action == "dev_grace" and request.user.is_platform_admin:
            install_dev_grace_license()
            messages.info(request, "Установлен dev grace (14 дней).")
            return redirect("licensing:status")
        if action == "recheck":
            info = check_license()
            messages.success(request, f"Статус лицензии: {info['status']}")
            return redirect("licensing:status")
        form = LicenseUploadForm(request.POST, request.FILES)
        if form.is_valid():
            ok, msg = install_license_file(form.cleaned_data["license_file"])
            if ok:
                messages.success(request, msg)
            else:
                messages.error(request, msg)
            return redirect("licensing:status")

    status_info = check_license()
    return render(
        request,
        "licensing/status.html",
        {
            "state": LicenseState.get_solo(),
            "status_info": status_info,
            "form": form,
            "fingerprint": machine_fingerprint(),
        },
    )
