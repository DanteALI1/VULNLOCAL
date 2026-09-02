from __future__ import annotations

import logging
from typing import Any

from .models import AuditEvent

logger = logging.getLogger(__name__)


def log_event(actor, action: str, message: str, **kwargs: Any) -> AuditEvent | None:
    """
    Persist an audit event. Never raises to callers.
    kwargs: object_type, object_id, ip, request
    """
    try:
        ip = kwargs.get("ip")
        request = kwargs.get("request")
        if ip is None and request is not None:
            ip = _client_ip(request)
        return AuditEvent.objects.create(
            actor=actor if getattr(actor, "is_authenticated", False) else None,
            action=action[:64],
            object_type=(kwargs.get("object_type") or "")[:64],
            object_id=str(kwargs.get("object_id") or "")[:64],
            message=message or "",
            ip=ip,
        )
    except Exception:
        logger.exception("audit.log_event failed")
        return None


def _client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
