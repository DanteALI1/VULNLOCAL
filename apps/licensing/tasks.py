import logging

import httpx
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import LicenseState
from .services import check_license, machine_fingerprint

logger = logging.getLogger(__name__)


@shared_task(name="apps.licensing.tasks.license_heartbeat")
def license_heartbeat():
    """Call license server heartbeat URL if configured; refresh local state."""
    state = LicenseState.get_solo()
    info = check_license()
    server_url = (state.server_url or getattr(settings, "LICENSE_SERVER_URL", "") or "").rstrip("/")
    if not server_url:
        logger.info("license_heartbeat: no server_url, local status=%s", info.get("status"))
        return info

    payload = {
        "fingerprint": state.fingerprint or machine_fingerprint(),
        "status": state.status,
        "expires_at": state.expires_at.isoformat() if state.expires_at else None,
        "org": (state.payload or {}).get("org"),
    }
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(f"{server_url}/api/v1/heartbeat", json=payload)
            resp.raise_for_status()
            data = resp.json() if resp.content else {}
        state.last_check_at = timezone.now()
        if isinstance(data, dict):
            remote_status = data.get("status")
            if remote_status in {c.value for c in LicenseState.Status}:
                state.status = remote_status
            if data.get("public_notes"):
                state.public_notes = str(data["public_notes"])[:2000]
            state.payload = {**(state.payload or {}), "last_heartbeat": data}
        state.save()
        logger.info("license_heartbeat: ok status=%s", state.status)
    except Exception as exc:
        logger.warning("license_heartbeat: server call failed: %s", exc)
        state.last_check_at = timezone.now()
        state.save(update_fields=["last_check_at", "updated_at"])
    return check_license()
