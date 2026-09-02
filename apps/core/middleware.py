from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin


SETUP_EXEMPT_PREFIXES = (
    "/setup/",
    "/static/",
    "/media/",
    "/healthz",
    "/readyz",
    "/admin/login",
)


class SetupRequiredMiddleware(MiddlewareMixin):
    def process_request(self, request):
        path = request.path
        if any(path.startswith(p) for p in SETUP_EXEMPT_PREFIXES):
            return None
        try:
            from .models import SystemSettings
            settings_obj = SystemSettings.get_solo()
        except Exception:
            # DB not ready / migrations pending
            if not path.startswith("/setup/"):
                return redirect("setup")
            return None
        if not settings_obj.setup_completed and not path.startswith("/setup/"):
            return redirect("setup")
        return None
