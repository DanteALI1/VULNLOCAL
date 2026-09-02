from __future__ import annotations

import logging
from typing import Any

import httpx
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _mail_settings():
    """Prefer SystemSettings overrides when present."""
    host = getattr(settings, "EMAIL_HOST", "") or ""
    port = getattr(settings, "EMAIL_PORT", 587)
    user = getattr(settings, "EMAIL_HOST_USER", "") or ""
    password = getattr(settings, "EMAIL_HOST_PASSWORD", "") or ""
    use_tls = getattr(settings, "EMAIL_USE_TLS", True)
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "novatip@localhost")
    try:
        from apps.core.models import SystemSettings

        s = SystemSettings.get_solo()
        if s.email_host:
            host = s.email_host
            port = s.email_port or port
            user = s.email_user or user
            password = s.email_password or password
            use_tls = s.email_use_tls
    except Exception:
        pass
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "use_tls": use_tls,
        "from_email": from_email,
    }


def send_email_notification(subject: str, message: str, recipients: list[str] | None = None) -> bool:
    """Best-effort SMTP notification."""
    recipients = [r for r in (recipients or []) if r]
    if not recipients:
        logger.debug("send_email_notification: no recipients")
        return False
    cfg = _mail_settings()
    if not cfg["host"]:
        logger.info("send_email_notification: EMAIL_HOST not configured")
        return False
    try:
        # Apply dynamic connection settings for this process
        settings.EMAIL_HOST = cfg["host"]
        settings.EMAIL_PORT = cfg["port"]
        settings.EMAIL_HOST_USER = cfg["user"]
        settings.EMAIL_HOST_PASSWORD = cfg["password"]
        settings.EMAIL_USE_TLS = cfg["use_tls"]
        send_mail(
            subject=subject,
            message=message,
            from_email=cfg["from_email"],
            recipient_list=recipients,
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception("send_email_notification failed")
        return False


def _telegram_creds():
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "") or ""
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "") or ""
    try:
        from apps.core.models import SystemSettings

        s = SystemSettings.get_solo()
        token = s.telegram_bot_token or token
        chat_id = s.telegram_chat_id or chat_id
    except Exception:
        pass
    return token, chat_id


def send_telegram_notification(text: str, chat_id: str | None = None) -> bool:
    """Best-effort Telegram Bot API message."""
    token, default_chat = _telegram_creds()
    chat_id = chat_id or default_chat
    if not token or not chat_id:
        logger.info("send_telegram_notification: bot token/chat_id not configured")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, json={"chat_id": chat_id, "text": text[:4000]})
            resp.raise_for_status()
        return True
    except Exception:
        logger.exception("send_telegram_notification failed")
        return False


def notify_ticket_event(ticket, event: str, actor=None, **kwargs: Any) -> None:
    """
    Notify interested parties about a ticket event (best-effort, never raises).
    """
    try:
        number = getattr(ticket, "number", "?")
        status = getattr(ticket, "status", "")
        title = getattr(ticket, "title", "")
        actor_name = ""
        if actor is not None:
            actor_name = getattr(actor, "display_name", lambda: str(actor))()
        body = f"NovaTIP T-{number}: {event}\n{title}\nstatus={status}\nby={actor_name}"
        subject = f"[NovaTIP] T-{number} {event}"

        recipients: list[str] = []
        for user in filter(None, [getattr(ticket, "reporter", None), getattr(ticket, "assignee", None)]):
            email = getattr(user, "email", "") or ""
            if email and email not in recipients:
                recipients.append(email)

        send_email_notification(subject, body, recipients)
        send_telegram_notification(body)
    except Exception:
        logger.exception("notify_ticket_event failed")
