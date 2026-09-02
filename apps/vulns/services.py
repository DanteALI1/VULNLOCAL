from __future__ import annotations

import logging
import re
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.core.models import SystemSettings

from .models import LocalIdCounter, Vulnerability

logger = logging.getLogger(__name__)

RESERVED_PREFIXES = {"CVE", "BDU"}
PREFIX_RE = re.compile(r"^[A-Za-z0-9]{2,16}$")


def allocate_local_id(prefix: str | None = None) -> str:
    """
    Allocate next local vulnerability id: {PREFIX}-YYYY-NNNN.
    Prefix comes from argument or SystemSettings.local_id_prefix.
    """
    settings_obj = SystemSettings.get_solo()
    prefix = (prefix or settings_obj.local_id_prefix or "").strip().upper()
    if not prefix or not PREFIX_RE.match(prefix):
        raise ValueError("Некорректный префикс локальных ID (2–16 латиница/цифры)")
    if prefix in RESERVED_PREFIXES:
        raise ValueError(f"Префикс {prefix} зарезервирован")

    year = timezone.now().year
    with transaction.atomic():
        counter, _ = (
            LocalIdCounter.objects.select_for_update()
            .get_or_create(year=year, prefix=prefix, defaults={"last_value": 0})
        )
        counter.last_value += 1
        counter.save(update_fields=["last_value"])
        seq = counter.last_value
    return f"{prefix}-{year}-{seq:04d}"


def _merge_json_lists(a: Any, b: Any) -> list:
    left = list(a or []) if isinstance(a, list) else ([] if a in (None, "") else [a])
    right = list(b or []) if isinstance(b, list) else ([] if b in (None, "") else [b])
    seen = set()
    out = []
    for item in left + right:
        key = item if not isinstance(item, (dict, list)) else repr(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def merge_bdu_into_cve(
    cve: Vulnerability,
    *,
    description_bdu: str = "",
    raw_bdu: dict | None = None,
    cwe=None,
    references=None,
    title: str = "",
) -> Vulnerability:
    """Enrich an existing CVE card with BDU data (no duplicate row)."""
    if description_bdu:
        cve.description_bdu = description_bdu
    if raw_bdu is not None:
        cve.raw_bdu = raw_bdu
    if title and not cve.title:
        cve.title = title[:512]
    if cwe is not None:
        cve.cwe = _merge_json_lists(cve.cwe, cwe)
    if references is not None:
        cve.references = _merge_json_lists(cve.references, references)
    if cve.source == Vulnerability.Source.NVD:
        cve.source = Vulnerability.Source.MERGED
    elif cve.source == Vulnerability.Source.BDU:
        cve.source = Vulnerability.Source.MERGED
    cve.save()
    return cve


def severity_from_score(score: float | None) -> str:
    if score is None:
        return Vulnerability.Severity.UNKNOWN
    try:
        s = float(score)
    except (TypeError, ValueError):
        return Vulnerability.Severity.UNKNOWN
    if s >= 9.0:
        return Vulnerability.Severity.CRITICAL
    if s >= 7.0:
        return Vulnerability.Severity.HIGH
    if s >= 4.0:
        return Vulnerability.Severity.MEDIUM
    if s > 0:
        return Vulnerability.Severity.LOW
    return Vulnerability.Severity.NONE
