"""[E] Walk policy_table.json. Table is data; engine does not hard-code outcome branches."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from namesake.checks import (
    countries_overlap,
    dob_agrees,
    name_agrees,
    run_checks,
)
from namesake.facts import CheckResult, HitFacts, Person
from namesake.resources import load_json
from namesake.store import DataStore


def _is_company(entity_type: str) -> bool:
    return (entity_type or "").lower() == "company"


def decide_one_person(
    person: Person, hit: HitFacts, store: DataStore
) -> Tuple[str, str, List[str], Dict[str, Any]]:
    """Return decision, reason_code, evidence, debug context."""
    checks = run_checks(person, hit, store)
    n_ok = name_agrees(person, hit, store)
    d_ok = dob_agrees(person, hit)
    name_dob_agree = n_ok is True and d_ok is True
    loc = checks["LOCATION_MISMATCH"]
    overlap = countries_overlap(person, hit)

    # Evaluate predicates referenced by the JSON table
    predicates: Dict[str, bool] = {
        "ENTITY_TYPE_MISMATCH": checks["ENTITY_TYPE_MISMATCH"].is_true,
        "DECEASED": checks["DECEASED"].is_true,
        "TEMPORAL_IMPOSSIBILITY": checks["TEMPORAL_IMPOSSIBILITY"].is_true,
        "DOB_MISMATCH": checks["DOB_MISMATCH"].is_true,
        "NAME_MISMATCH_VERIFIED": checks["NAME_MISMATCH_VERIFIED"].is_true,
        "LOCATION_MISMATCH": loc.is_true and not name_dob_agree,
        "LOCATION_MISMATCH_BUT_NAME_DOB_AGREE": loc.is_true and name_dob_agree,
        "NAME_AND_DOB_AGREE": name_dob_agree,
        "NAME_DOB_LOCATION_MATCH": (
            not _is_company(hit.entity_type)
            and name_dob_agree
            and overlap
            and not _any_clearance_or_blocking(checks, name_dob_agree)
        ),
        "NAME_DOB_MATCH": (
            not _is_company(hit.entity_type)
            and name_dob_agree
            and not overlap
            and not _any_clearance_or_blocking(checks, name_dob_agree)
        ),
        "NAME_LOCATION_MATCH": (
            _is_company(hit.entity_type)
            and n_ok is True
            and overlap
            and not _any_clearance_or_blocking(checks, False)
        ),
        "DEFAULT": True,
    }

    table = load_json("policy_table.json")
    for row in table["rows"]:
        when = row["when"]
        if when == "DEFAULT":
            decision = row["decision"]
            code = row["reason_code"]
            return (
                decision,
                code,
                _evidence_for_review(person, hit, checks),
                {
                    "checks": checks,
                    "name_ok": n_ok,
                    "dob_ok": d_ok,
                },
            )
        if not predicates.get(when):
            continue
        blocked = row.get("blocked_when")
        if blocked and predicates.get(blocked):
            continue
        decision = row["decision"]
        code = row["reason_code"]
        evidence = _evidence_for(code, checks, person, hit)
        return (
            decision,
            code,
            evidence,
            {
                "checks": checks,
                "name_ok": n_ok,
                "dob_ok": d_ok,
                "row": row["id"],
            },
        )

    return (
        "REVIEW",
        "INSUFFICIENT_DATA",
        _evidence_for_review(person, hit, checks),
        {"checks": checks},
    )


def _any_clearance_or_blocking(checks: Dict[str, CheckResult], name_dob_agree: bool) -> bool:
    """TRUE clearance, or UNKNOWN that could hide a contradiction.

    LOCATION UNKNOWN (open country set, I9) blocks location clearance only —
    it does not block NAME_DOB_MATCH confirmation.
    """
    for key, cr in checks.items():
        if key == "LOCATION_MISMATCH":
            if name_dob_agree:
                continue
            if cr.is_true:
                return True
            continue
        if cr.is_true:
            return True
        if cr.is_unknown and key in {
            "DOB_MISMATCH",
            "TEMPORAL_IMPOSSIBILITY",
            "NAME_MISMATCH_VERIFIED",
            "DECEASED",
            "ENTITY_TYPE_MISMATCH",
        }:
            return True
    return False


def _evidence_for(
    code: str, checks: Dict[str, CheckResult], person: Person, hit: HitFacts
) -> List[str]:
    cr = checks.get(code)
    if cr and cr.evidence:
        return [e for e in cr.evidence if e]
    ev = list(person.evidence_ids[:2]) + list(hit.evidence_ids[:1])
    return [e for e in ev if e]


def _evidence_for_review(
    person: Person, hit: HitFacts, checks: Dict[str, CheckResult]
) -> List[str]:
    ev = list(person.evidence_ids[:2]) + list(hit.evidence_ids[:1])
    return [e for e in ev if e]


def aggregate_persons(
    results: List[Tuple[str, str, List[str], Dict[str, Any], Person]],
) -> Tuple[str, str, Optional[str], List[str], Dict[str, Any]]:
    """I7: same decision → emit it with AMBIGUOUS id; else REVIEW / AMBIGUOUS_CUSTOMER_RECORD."""
    if not results:
        return "REVIEW", "INSUFFICIENT_DATA", None, [], {}
    if len(results) == 1:
        d, c, ev, ctx, person = results[0]
        return d, c, person.primary_id, ev, ctx
    decisions = {r[0] for r in results}
    record_id = "AMBIGUOUS"
    if len(decisions) == 1:
        d = results[0][0]
        # Prefer shortest proof among same decision (I8)
        best = min(results, key=lambda r: len(r[2]))
        return d, best[1], record_id, best[2], best[3]
    # merge evidence lightly
    ev: List[str] = []
    for r in results:
        for e in r[2]:
            if e not in ev:
                ev.append(e)
    return "REVIEW", "AMBIGUOUS_CUSTOMER_RECORD", record_id, ev, {}
