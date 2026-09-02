from __future__ import annotations

from apps.accounts.models import User

from .models import Ticket

# Declarative transition map (from → allowed to). Extra rules in can_transition.
TRANSITIONS: dict[str, set[str]] = {
    Ticket.Status.NEW: {Ticket.Status.TRIAGE, Ticket.Status.REJECTED},
    Ticket.Status.TRIAGE: {Ticket.Status.IN_PROGRESS, Ticket.Status.REJECTED},
    Ticket.Status.IN_PROGRESS: {Ticket.Status.WAITING, Ticket.Status.RESOLVED},
    Ticket.Status.WAITING: {Ticket.Status.IN_PROGRESS, Ticket.Status.RESOLVED},
    Ticket.Status.RESOLVED: {Ticket.Status.CLOSED, Ticket.Status.IN_PROGRESS},
    Ticket.Status.CLOSED: set(),
    Ticket.Status.REJECTED: set(),
}


def _is_admin(user) -> bool:
    return bool(getattr(user, "is_platform_admin", False))


def _is_analyst(user) -> bool:
    return _is_admin(user) or getattr(user, "role", None) == User.Role.ANALYST


def _is_verifier(user) -> bool:
    return (
        getattr(user, "role", None) == User.Role.VERIFIER
        or bool(getattr(user, "is_verifier", False))
        or _is_admin(user)
    )


def _is_ticket_assignee(user, ticket: Ticket) -> bool:
    return ticket.assignee_id is not None and ticket.assignee_id == getattr(user, "id", None)


def _is_reporter(user, ticket: Ticket) -> bool:
    return ticket.reporter_id == getattr(user, "id", None)


def can_create(user) -> bool:
    """create: analyst/admin"""
    return _is_analyst(user)


def can_assign(user, assignee) -> bool:
    """assign: analyst/admin to assignee role (ticket_assignee)"""
    if not _is_analyst(user) or assignee is None:
        return False
    return getattr(assignee, "role", None) == User.Role.TICKET_ASSIGNEE


def can_transition(user, ticket: Ticket, new_status: str, *, force: bool = False) -> tuple[bool, str]:
    """
    Enforce ticket status transition matrix.
    Returns (allowed, reason).
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False, "Требуется аутентификация"

    old = ticket.status
    if old == new_status:
        return False, "Статус не изменился"

    # Force close: platform_admin only
    if force and new_status == Ticket.Status.CLOSED:
        if _is_admin(user):
            return True, "ok"
        return False, "Force close доступен только platform_admin"

    allowed_targets = TRANSITIONS.get(old, set())
    if new_status not in allowed_targets:
        return False, f"Переход {old} → {new_status} не предусмотрен"

    # triage → in_progress: assignee accept or analyst
    if old == Ticket.Status.TRIAGE and new_status == Ticket.Status.IN_PROGRESS:
        if not ticket.assignee_id:
            return False, "Сначала назначьте исполнителя"
        if _is_analyst(user) or _is_ticket_assignee(user, ticket):
            return True, "ok"
        return False, "Принять в работу может исполнитель или аналитик"

    # in_progress ↔ waiting: assignee
    if {old, new_status} == {Ticket.Status.IN_PROGRESS, Ticket.Status.WAITING}:
        if not (_is_ticket_assignee(user, ticket) or _is_admin(user)):
            return False, "Только исполнитель может менять waiting"
        if new_status == Ticket.Status.WAITING and not (ticket.waiting_reason or "").strip():
            return False, "Укажите причину ожидания"
        return True, "ok"

    # → resolved: ONLY assignee or admin, resolution required
    if new_status == Ticket.Status.RESOLVED:
        if not (_is_ticket_assignee(user, ticket) or _is_admin(user)):
            return False, "Резолвить может только исполнитель или admin"
        if not (ticket.resolution_notes or "").strip():
            return False, "Требуется описание устранения"
        return True, "ok"

    # resolved → closed: reporter or verifier (NOT assignee)
    if old == Ticket.Status.RESOLVED and new_status == Ticket.Status.CLOSED:
        if _is_ticket_assignee(user, ticket) and not _is_admin(user):
            return False, "Исполнитель не может закрыть заявку"
        if _is_reporter(user, ticket) or _is_verifier(user):
            return True, "ok"
        return False, "Закрыть может постановщик или verifier"

    # resolved → in_progress: reporter/verifier with reason
    if old == Ticket.Status.RESOLVED and new_status == Ticket.Status.IN_PROGRESS:
        if not (_is_reporter(user, ticket) or _is_verifier(user)):
            return False, "Вернуть в работу может постановщик или verifier"
        if not (ticket.reopen_reason or "").strip():
            return False, "Укажите причину возврата"
        return True, "ok"

    # → rejected: analyst from new/triage
    if new_status == Ticket.Status.REJECTED:
        if old not in {Ticket.Status.NEW, Ticket.Status.TRIAGE}:
            return False, "Отклонить можно только из new/triage"
        if not _is_analyst(user):
            return False, "Отклонить может аналитик"
        if not (ticket.reject_reason or "").strip():
            return False, "Укажите причину отклонения"
        return True, "ok"

    # new → triage: analyst/admin
    if old == Ticket.Status.NEW and new_status == Ticket.Status.TRIAGE:
        if _is_analyst(user):
            return True, "ok"
        return False, "Только аналитик"

    if _is_admin(user) or _is_analyst(user) or _is_ticket_assignee(user, ticket):
        return True, "ok"
    return False, "Недостаточно прав"


def available_actions(user, ticket: Ticket) -> list[dict]:
    """UI helper: list of possible transition actions for current user."""
    actions = []
    # Probe with temporary reason fields so required-text rules don't hide buttons
    saved = {
        "waiting_reason": ticket.waiting_reason,
        "resolution_notes": ticket.resolution_notes,
        "reject_reason": ticket.reject_reason,
        "reopen_reason": ticket.reopen_reason,
    }
    try:
        if not (ticket.waiting_reason or "").strip():
            ticket.waiting_reason = "(pending)"
        if not (ticket.resolution_notes or "").strip():
            ticket.resolution_notes = "(pending)"
        if not (ticket.reject_reason or "").strip():
            ticket.reject_reason = "(pending)"
        if not (ticket.reopen_reason or "").strip():
            ticket.reopen_reason = "(pending)"
        for target in sorted(TRANSITIONS.get(ticket.status, set())):
            ok, _ = can_transition(user, ticket, target)
            if ok:
                actions.append(
                    {
                        "status": target,
                        "label": dict(Ticket.Status.choices).get(target, target),
                    }
                )
    finally:
        ticket.waiting_reason = saved["waiting_reason"]
        ticket.resolution_notes = saved["resolution_notes"]
        ticket.reject_reason = saved["reject_reason"]
        ticket.reopen_reason = saved["reopen_reason"]

    if ticket.status != Ticket.Status.CLOSED and _is_admin(user):
        if not any(a["status"] == Ticket.Status.CLOSED for a in actions):
            actions.append(
                {
                    "status": Ticket.Status.CLOSED,
                    "label": "Force close",
                    "force": True,
                }
            )
    return actions
