"""Output line shape and light validation (mirrors output.schema.json)."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

HIT_RE = re.compile(r"^H-[0-9A-F]{6}$")
ALERT_RE = re.compile(r"^A-[0-9A-F]{6}$")
CUS_RE = re.compile(r"^(CUS-[0-9]{6}|AMBIGUOUS)$")

DECISIONS = frozenset({"DIFFERENT_ENTITY", "SAME_ENTITY", "REVIEW"})

CODES_BY_DECISION = {
    "DIFFERENT_ENTITY": frozenset(
        {
            "TEMPORAL_IMPOSSIBILITY",
            "DOB_MISMATCH",
            "LOCATION_MISMATCH",
            "NAME_MISMATCH_VERIFIED",
            "ENTITY_TYPE_MISMATCH",
            "DECEASED",
        }
    ),
    "SAME_ENTITY": frozenset(
        {
            "NAME_DOB_LOCATION_MATCH",
            "NAME_DOB_MATCH",
            "NAME_LOCATION_MATCH",
        }
    ),
    "REVIEW": frozenset({"INSUFFICIENT_DATA", "AMBIGUOUS_CUSTOMER_RECORD"}),
}


def make_line(
    hit_id: str,
    alert_id: str,
    decision: str,
    reason_code: str,
    customer_record_id: Optional[str],
    reason: str,
    evidence: List[str],
) -> Dict[str, Any]:
    return {
        "hit_id": hit_id,
        "alert_id": alert_id,
        "decision": decision,
        "reason_code": reason_code,
        "customer_record_id": customer_record_id,
        "reason": reason,
        "evidence": list(evidence),
    }


def validate_line(row: Dict[str, Any]) -> Optional[str]:
    """Return an error string, or None if the line is schema-OK."""
    if not isinstance(row, dict):
        return "not an object"
    hit_id = row.get("hit_id")
    if not isinstance(hit_id, str) or not HIT_RE.match(hit_id):
        return f"bad hit_id {hit_id!r}"
    alert_id = row.get("alert_id")
    if not isinstance(alert_id, str) or not ALERT_RE.match(alert_id):
        return f"bad alert_id {alert_id!r}"
    decision = row.get("decision")
    if decision not in DECISIONS:
        return f"bad decision {decision!r}"
    reason_code = row.get("reason_code")
    if reason_code not in CODES_BY_DECISION[decision]:
        return f"reason_code {reason_code!r} does not belong to {decision}"
    record = row.get("customer_record_id")
    if record is not None and (not isinstance(record, str) or not CUS_RE.match(record)):
        return f"bad customer_record_id {record!r}"
    reason = row.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        return "empty reason"
    evidence = row.get("evidence")
    if not isinstance(evidence, list) or any(not isinstance(x, str) for x in evidence):
        return "evidence must be a list of strings"
    return None


def dumps_line(row: Dict[str, Any]) -> str:
    err = validate_line(row)
    if err:
        raise ValueError(err)
    return json.dumps(row, ensure_ascii=False, separators=(",", ":"))
