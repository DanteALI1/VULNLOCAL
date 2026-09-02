from __future__ import annotations

import hashlib
import hmac
import json
import logging
import platform
import socket
import uuid
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import LicenseState

logger = logging.getLogger(__name__)

GRACE_DAYS = 14


def machine_fingerprint() -> str:
    """Stable-ish machine fingerprint for license binding (MVP)."""
    parts = [
        platform.node() or "",
        platform.system() or "",
        platform.machine() or "",
        socket.gethostname() or "",
        str(uuid.getnode()),
    ]
    raw = "|".join(parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _canonical_payload(data: dict[str, Any]) -> bytes:
    body = {k: data[k] for k in ("org", "seats", "expires") if k in data}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _verify_signature(data: dict[str, Any]) -> tuple[bool, str]:
    signature = (data.get("signature") or "").strip()
    if not signature:
        if settings.DEBUG:
            return True, "unsigned accepted (DEBUG)"
        return False, "Подпись лицензии отсутствует"
    secret = settings.SECRET_KEY.encode("utf-8")
    expected = hmac.new(secret, _canonical_payload(data), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return False, "Неверная подпись лицензии"
    return True, "ok"


def _parse_expires(value: Any):
    if value is None or value == "":
        return None
    if hasattr(value, "isoformat"):
        return value
    text = str(value).strip()
    dt = parse_datetime(text)
    if dt is None:
        # date-only YYYY-MM-DD → end of day UTC-ish aware
        try:
            from datetime import date, datetime, time as dtime

            d = date.fromisoformat(text)
            dt = datetime.combine(d, dtime(23, 59, 59))
        except ValueError:
            return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def install_license_file(uploaded_file) -> tuple[bool, str]:
    """
    Accept JSON .novalic with fields {org, seats, expires, signature}.
    MVP: verify HMAC-SHA256(SECRET_KEY) over canonical org/seats/expires,
    or accept unsigned files when DEBUG=True.
    """
    try:
        raw = uploaded_file.read()
        if isinstance(raw, bytes):
            text = raw.decode("utf-8")
        else:
            text = str(raw)
        data = json.loads(text)
    except Exception as exc:
        return False, f"Не удалось прочитать файл лицензии: {exc}"

    if not isinstance(data, dict):
        return False, "Лицензия должна быть JSON-объектом"

    ok, msg = _verify_signature(data)
    if not ok:
        return False, msg

    expires_at = _parse_expires(data.get("expires"))
    if expires_at is None:
        return False, "Поле expires отсутствует или некорректно"

    now = timezone.now()
    state = LicenseState.get_solo()
    state.fingerprint = machine_fingerprint()
    state.payload = {
        "org": data.get("org"),
        "seats": data.get("seats"),
        "expires": data.get("expires"),
        "signed": bool(data.get("signature")),
    }
    state.expires_at = expires_at
    state.grace_until = expires_at + timedelta(days=GRACE_DAYS)
    state.last_check_at = now
    state.public_notes = f"Организация: {data.get('org', '—')}; мест: {data.get('seats', '—')}"
    if expires_at > now:
        state.status = LicenseState.Status.VALID
    elif state.grace_until and state.grace_until > now:
        state.status = LicenseState.Status.GRACE
    else:
        state.status = LicenseState.Status.INVALID
        state.save()
        return False, "Срок лицензии истёк"

    state.save()
    return True, f"Лицензия установлена ({state.get_status_display()})"


def install_dev_grace_license() -> LicenseState:
    """Install a 14-day development grace license (no file)."""
    now = timezone.now()
    state = LicenseState.get_solo()
    state.fingerprint = machine_fingerprint()
    state.expires_at = now
    state.grace_until = now + timedelta(days=GRACE_DAYS)
    state.status = LicenseState.Status.GRACE
    state.last_check_at = now
    state.payload = {"org": "DEV", "seats": 0, "dev_grace": True}
    state.public_notes = f"Dev grace до {state.grace_until.isoformat()}"
    state.save()
    return state


def check_license() -> dict[str, Any]:
    """Re-evaluate local license state and return a status dict."""
    state = LicenseState.get_solo()
    if not state.fingerprint:
        state.fingerprint = machine_fingerprint()
    prev = state.status
    state.refresh_status_from_dates()
    state.last_check_at = timezone.now()
    state.save(
        update_fields=[
            "status",
            "fingerprint",
            "last_check_at",
            "updated_at",
        ]
    )
    return {
        "status": state.status,
        "previous_status": prev,
        "expires_at": state.expires_at.isoformat() if state.expires_at else None,
        "grace_until": state.grace_until.isoformat() if state.grace_until else None,
        "fingerprint": state.fingerprint,
        "server_url": state.server_url,
        "last_check_at": state.last_check_at.isoformat() if state.last_check_at else None,
        "payload": state.payload or {},
        "public_notes": state.public_notes,
        "operation_allowed": is_operation_allowed(),
    }


def is_operation_allowed() -> bool:
    """True when license is valid or within grace period."""
    state = LicenseState.get_solo()
    status = state.refresh_status_from_dates()
    LicenseState.objects.filter(pk=state.pk).update(status=status)
    return status in {
        LicenseState.Status.VALID,
        LicenseState.Status.GRACE,
    }
