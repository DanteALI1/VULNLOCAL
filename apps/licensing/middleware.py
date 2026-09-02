from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

from .services import is_operation_allowed


LICENSE_ALLOWED_PREFIXES = (
    "/licensing/",
    "/accounts/",
    "/healthz",
    "/readyz",
    "/static/",
    "/media/",
    "/setup/",
    "/admin/login",
)


class LicenseGateMiddleware(MiddlewareMixin):
    """
    After setup is completed, block the app when license is invalid
    (not in grace). Allow only licensing, accounts, health, static, setup.
    """

    def process_request(self, request):
        path = request.path
        if any(path.startswith(p) for p in LICENSE_ALLOWED_PREFIXES):
            return None
        try:
            from apps.core.models import SystemSettings

            settings_obj = SystemSettings.get_solo()
        except Exception:
            return None
        if not settings_obj.setup_completed:
            return None
        try:
            allowed = is_operation_allowed()
        except Exception:
            # DB/migrations not ready — do not block hard
            return None
        if not allowed:
            return redirect("licensing:status")
        return None
