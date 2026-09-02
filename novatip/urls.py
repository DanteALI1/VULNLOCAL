from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.core.views_setup import SetupWizardView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("setup/", SetupWizardView.as_view(), name="setup"),
    path("licensing/", include("apps.licensing.urls")),
    path("vulns/", include("apps.vulns.urls")),
    path("tickets/", include("apps.tickets.urls")),
    path("audit/", include("apps.audit.urls")),
    path("", include("apps.core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
