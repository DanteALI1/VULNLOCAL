from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, render
from django.views import View

from apps.audit.services import log_event
from apps.licensing.services import install_dev_grace_license, install_license_file

from .db_wizard import (
    DbParams,
    create_role_and_database,
    test_connection,
    write_database_url_to_env,
)
from .forms import (
    LicenseStepForm,
    OrgStepForm,
    BrandingStepForm,
    DbConnectForm,
    DbCreateForm,
    AdminStepForm,
    SourcesStepForm,
    MailStepForm,
    TelegramStepForm
)
from .models import SetupProgress, SystemSettings

User = get_user_model()

STEPS = [
    (1, "Лицензия"),
    (2, "Организация"),
    (3, "Оформление"),
    (4, "База данных"),
    (5, "Администратор"),
    (6, "Источники"),
    (7, "Почта"),
    (8, "Telegram"),
    (9, "Финиш"),
]


class SetupWizardView(View):
    template_name = "core/setup_wizard.html"

    def get(self, request):
        if SystemSettings.get_solo().setup_completed:
            return redirect("core:dashboard")
        step = int(request.GET.get("step", SetupProgress.get_solo().current_step or 1))
        return self._render(request, step)

    def post(self, request):
        step = int(request.POST.get("step", 1))
        handler = getattr(self, f"_step_{step}", None)
        if handler is None:
            messages.error(request, "Неизвестный шаг")
            return redirect("setup")
        return handler(request)

    def _render(self, request, step, form=None, extra=None):
        ctx = {
            "steps": STEPS,
            "step": step,
            "step_title": dict(STEPS).get(step, ""),
            "form": form,
            "settings_obj": SystemSettings.get_solo(),
            "db_mode": (extra or {}).get("db_mode")
            or request.GET.get("db_mode")
            or "connect",
        }
        if extra:
            ctx.update(extra)
        return render(request, self.template_name, ctx)

    def _mark(self, step: int) -> None:
        prog = SetupProgress.get_solo()
        done = set(prog.completed_steps or [])
        done.add(step)
        prog.completed_steps = sorted(done)
        prog.current_step = min(step + 1, 9)
        prog.save()

    def _step_1(self, request):
        form = LicenseStepForm(request.POST, request.FILES)
        if not form.is_valid():
            return self._render(request, 1, form)
        if form.cleaned_data.get("license_file"):
            ok, msg = install_license_file(form.cleaned_data["license_file"])
            if not ok:
                messages.error(request, msg)
                return self._render(request, 1, form)
            messages.success(request, msg)
        elif form.cleaned_data.get("skip_for_dev"):
            install_dev_grace_license()
            messages.info(request, "Установлен dev grace-лицензионный статус (14 дней).")
        else:
            messages.error(request, "Загрузите лицензию или отметьте dev-режим.")
            return self._render(request, 1, form)
        url = form.cleaned_data.get("license_server_url")
        if url:
            from apps.licensing.models import LicenseState

            st = LicenseState.get_solo()
            st.server_url = url
            st.save(update_fields=["server_url"])
        self._mark(1)
        return redirect(f"{request.path}?step=2")

    def _step_2(self, request):
        form = OrgStepForm(request.POST)
        if not form.is_valid():
            return self._render(request, 2, form)
        s = SystemSettings.get_solo()
        s.organization_name = form.cleaned_data["organization_name"]
        s.local_id_prefix = form.cleaned_data["local_id_prefix"]
        s.save()
        self._mark(2)
        return redirect(f"{request.path}?step=3")

    def _step_3(self, request):
        form = BrandingStepForm(request.POST, request.FILES)
        if not form.is_valid():
            return self._render(request, 3, form)
        s = SystemSettings.get_solo()
        s.login_title = form.cleaned_data["login_title"]
        s.login_subtitle = form.cleaned_data.get("login_subtitle") or ""
        if form.cleaned_data.get("logo"):
            s.logo = form.cleaned_data["logo"]
        s.save()
        self._mark(3)
        return redirect(f"{request.path}?step=4")

    def _step_4(self, request):
        mode = request.POST.get("db_mode", "connect")
        if mode == "create":
            form = DbCreateForm(request.POST)
            if not form.is_valid():
                return self._render(request, 4, form, {"db_mode": "create"})
            cd = form.cleaned_data
            ok, msg, params = create_role_and_database(
                host=cd["host"],
                port=cd["port"],
                superuser=cd["superuser"],
                super_password=cd["super_password"],
                db_name=cd["db_name"],
                role_name=cd["role_name"],
                role_password=cd["role_password"],
                sslmode=cd["sslmode"],
            )
            if not ok or params is None:
                messages.error(request, msg)
                return self._render(request, 4, form, {"db_mode": "create"})
            messages.success(request, msg)
        else:
            form = DbConnectForm(request.POST)
            if not form.is_valid():
                return self._render(request, 4, form, {"db_mode": "connect"})
            cd = form.cleaned_data
            params = DbParams(
                host=cd["host"],
                port=cd["port"],
                name=cd["name"],
                user=cd["user"],
                password=cd["password"],
                sslmode=cd["sslmode"],
            )
            action = request.POST.get("action", "save")
            ok, msg = test_connection(params)
            if action == "test":
                (messages.success if ok else messages.error)(request, msg)
                return self._render(request, 4, form, {"db_mode": "connect"})
            if not ok:
                messages.error(request, msg)
                return self._render(request, 4, form, {"db_mode": "connect"})
            messages.success(request, msg)

        write_database_url_to_env(params.as_url(), Path(settings.BASE_DIR) / ".env")
        s = SystemSettings.get_solo()
        s.db_host = params.host
        s.db_port = params.port
        s.db_name = params.name
        s.db_user = params.user
        s.db_sslmode = params.sslmode
        s.save()
        log_event(
            request.user if request.user.is_authenticated else None,
            "db.setup",
            f"{params.host}:{params.port}/{params.name}",
        )
        self._mark(4)
        return redirect(f"{request.path}?step=5")

    def _step_5(self, request):
        form = AdminStepForm(request.POST)
        if not form.is_valid():
            return self._render(request, 5, form)
        cd = form.cleaned_data
        user, _ = User.objects.get_or_create(
            username=cd["username"],
            defaults={
                "email": cd["email"],
                "full_name": cd.get("full_name") or "",
                "role": User.Role.PLATFORM_ADMIN,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        user.set_password(cd["password1"])
        user.email = cd["email"]
        user.full_name = cd.get("full_name") or ""
        user.role = User.Role.PLATFORM_ADMIN
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self._mark(5)
        return redirect(f"{request.path}?step=6")

    def _step_6(self, request):
        form = SourcesStepForm(request.POST)
        if not form.is_valid():
            return self._render(request, 6, form)
        s = SystemSettings.get_solo()
        s.nvd_api_key = form.cleaned_data.get("nvd_api_key") or ""
        s.kev_enabled = form.cleaned_data.get("kev_enabled", True)
        s.bdu_enabled = form.cleaned_data.get("bdu_enabled", True)
        s.save()
        self._mark(6)
        return redirect(f"{request.path}?step=7")

    def _step_7(self, request):
        form = MailStepForm(request.POST)
        if not form.is_valid():
            return self._render(request, 7, form)
        s = SystemSettings.get_solo()
        s.email_host = form.cleaned_data.get("email_host") or ""
        s.email_port = form.cleaned_data.get("email_port") or 587
        s.email_user = form.cleaned_data.get("email_user") or ""
        if form.cleaned_data.get("email_password"):
            s.email_password = form.cleaned_data["email_password"]
        s.email_use_tls = form.cleaned_data.get("email_use_tls", True)
        s.save()
        self._mark(7)
        return redirect(f"{request.path}?step=8")

    def _step_8(self, request):
        form = TelegramStepForm(request.POST)
        if not form.is_valid():
            return self._render(request, 8, form)
        if not form.cleaned_data.get("skip"):
            s = SystemSettings.get_solo()
            s.telegram_bot_token = form.cleaned_data.get("telegram_bot_token") or ""
            s.telegram_chat_id = form.cleaned_data.get("telegram_chat_id") or ""
            s.save()
        self._mark(8)
        return redirect(f"{request.path}?step=9")

    def _step_9(self, request):
        s = SystemSettings.get_solo()
        s.setup_completed = True
        s.save(update_fields=["setup_completed"])
        self._mark(9)
        try:
            from apps.vulns.tasks import sync_nvd_incremental

            sync_nvd_incremental.delay()
        except Exception:
            pass
        messages.success(request, "Мастер настройки завершён. Можно войти в NovaTIP.")
        return redirect("accounts:login")
