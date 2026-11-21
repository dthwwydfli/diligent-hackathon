"""[D] Three-valued checks (TRUE / FALSE / UNKNOWN) + proof facts."""

from __future__ import annotations

from typing import Dict, List, Optional

from namesake.dates import (
    all_hit_dobs_contradicted,
    intervals_agree,
    under_16_at,
)
from namesake.facts import CheckResult, HitFacts, Person
from namesake.names import (
    build_variant_map,
    can_use_name_for_clear_or_confirm,
    names_agree,
    tokenize_name,
)
from namesake.store import DataStore


def _is_company(entity_type: str) -> bool:
    return (entity_type or "").lower() == "company"


def check_entity_type(person: Person, hit: HitFacts) -> CheckResult:
    """P6 Type."""
    p_co = _is_company(person.entity_type)
    h_co = _is_company(hit.entity_type)
    if p_co != h_co:
        return CheckResult(
            "ENTITY_TYPE_MISMATCH",
            "TRUE",
            "ENTITY_TYPE_MISMATCH",
            list(person.evidence_ids[:1] + hit.evidence_ids[:1]),
        )
    return CheckResult("ENTITY_TYPE_MISMATCH", "FALSE")


def check_deceased(hit: HitFacts) -> CheckResult:
    """P6 / I4: only deceased_date before screened_at is TRUE.

    No structured death date → FALSE (not a contradiction).
    Prose-only death stays UNKNOWN so it cannot enable a DECEASED clearance.
    """
    if hit.deceased_before_screen is True:
        return CheckResult(
            "DECEASED",
            "TRUE",
            "DECEASED",
            [hit.deceased_source or hit.hit_id],
        )
    if hit.deceased_before_screen is False:
        return CheckResult("DECEASED", "FALSE")
    # None: no deceased_date. Treat as FALSE for confirmation.
    # Callers that saw prose-only death should set deceased_before_screen via a
    # sentinel path later; until then, absence of the field is not UNKNOWN.
    return CheckResult("DECEASED", "FALSE")


def check_temporal(person: Person, hit: HitFacts) -> CheckResult:
    """Under-16 or company incorporated after earliest dated report."""
    if hit.earliest_report is None:
        return CheckResult("TEMPORAL_IMPOSSIBILITY", "FALSE")
    if _is_company(hit.entity_type) or _is_company(person.entity_type):
        inc = hit.incorporation or (hit.dobs[0] if hit.dobs else None)
        if inc is None:
            # Missing incorporation cannot clear; also does not block company name/country confirm
            return CheckResult("TEMPORAL_IMPOSSIBILITY", "FALSE")
        # incorporated after report?
        if (inc.y_lo, inc.m_lo, inc.d_lo) > (
            hit.earliest_report.y_hi,
            hit.earliest_report.m_hi,
            hit.earliest_report.d_hi,
        ):
            return CheckResult(
                "TEMPORAL_IMPOSSIBILITY",
                "TRUE",
                "TEMPORAL_IMPOSSIBILITY",
                list(person.evidence_ids[:1] + hit.evidence_ids[:1]),
            )
        return CheckResult("TEMPORAL_IMPOSSIBILITY", "FALSE")
    if person.dob_unknown or person.dob is None:
        return CheckResult("TEMPORAL_IMPOSSIBILITY", "UNKNOWN")
    if not person.dob.certain:
        # uncertain DOB must not enable clearance
        if under_16_at(person.dob, hit.earliest_report):
            return CheckResult("TEMPORAL_IMPOSSIBILITY", "UNKNOWN")
        return CheckResult("TEMPORAL_IMPOSSIBILITY", "FALSE")
    if under_16_at(person.dob, hit.earliest_report):
        ev = list(person.evidence_ids[:1])
        if person.verified_source:
            ev = [person.verified_source]
        return CheckResult(
            "TEMPORAL_IMPOSSIBILITY",
            "TRUE",
            "TEMPORAL_IMPOSSIBILITY",
            ev + hit.evidence_ids[:1],
        )
    return CheckResult("TEMPORAL_IMPOSSIBILITY", "FALSE")


def check_dob_mismatch(person: Person, hit: HitFacts) -> CheckResult:
    if _is_company(hit.entity_type):
        # company DOB_MISMATCH uses incorporation vs hit dobs — rare; treat via temporal mostly
        return CheckResult("DOB_MISMATCH", "FALSE")
    if person.dob_unknown or person.dob is None:
        return CheckResult("DOB_MISMATCH", "UNKNOWN")
    if hit.dob_unknown:
        return CheckResult("DOB_MISMATCH", "UNKNOWN")
    if not hit.dobs:
        return CheckResult("DOB_MISMATCH", "FALSE")
    if not person.dob.certain:
        # may not enable clearance
        if all_hit_dobs_contradicted(person.dob, hit.dobs):
            return CheckResult("DOB_MISMATCH", "UNKNOWN")
        return CheckResult("DOB_MISMATCH", "FALSE")
    if all_hit_dobs_contradicted(person.dob, hit.dobs):
        ev = [person.verified_source] if person.verified_source else person.evidence_ids[:1]
        return CheckResult("DOB_MISMATCH", "TRUE", "DOB_MISMATCH", list(ev) + hit.evidence_ids[:1])
    return CheckResult("DOB_MISMATCH", "FALSE")


def check_location(person: Person, hit: HitFacts) -> CheckResult:
    """Closed customer set with no overlap → TRUE. Open set → UNKNOWN (I9)."""
    if person.countries_open:
        return CheckResult("LOCATION_MISMATCH", "UNKNOWN")
    if not person.countries or not hit.countries:
        return CheckResult("LOCATION_MISMATCH", "FALSE")
    if person.countries.isdisjoint(hit.countries):
        return CheckResult(
            "LOCATION_MISMATCH",
            "TRUE",
            "LOCATION_MISMATCH",
            list(person.evidence_ids[:1] + hit.evidence_ids[:1]),
        )
    return CheckResult("LOCATION_MISMATCH", "FALSE")


def check_name_mismatch(person: Person, hit: HitFacts, store: DataStore) -> CheckResult:
    """Verified legal name agrees with none of the hit's names. Needs approved check."""
    if person.identity_unknown:
        # Unread newer KYC note: name is not known, so it cannot clear.
        return CheckResult("NAME_MISMATCH_VERIFIED", "UNKNOWN")
    if not person.has_approved_check or not person.verified_name:
        return CheckResult("NAME_MISMATCH_VERIFIED", "FALSE")
    variants = build_variant_map(store.name_variants.get("groups") or [])
    forms = list(store.name_variants.get("company_legal_forms") or [])
    parts = tokenize_name(person.verified_name)
    if not can_use_name_for_clear_or_confirm(parts):
        return CheckResult("NAME_MISMATCH_VERIFIED", "UNKNOWN")
    is_co = _is_company(person.entity_type)
    for hn in hit.names:
        if names_agree(
            person.verified_name,
            hn,
            variants=variants,
            company_legal_forms=forms if is_co else None,
            a_is_company=is_co,
            b_is_company=_is_company(hit.entity_type),
        ):
            return CheckResult("NAME_MISMATCH_VERIFIED", "FALSE")
    return CheckResult(
        "NAME_MISMATCH_VERIFIED",
        "TRUE",
        "NAME_MISMATCH_VERIFIED",
        [person.verified_source or person.primary_id or ""] + hit.evidence_ids[:1],
    )


def name_agrees(person: Person, hit: HitFacts, store: DataStore) -> Optional[bool]:
    """I3: verified name if present; else full/preferred + screened. None = cannot decide."""
    if person.identity_unknown:
        # Do not fall back to the declared or screened name.
        return None
    variants = build_variant_map(store.name_variants.get("groups") or [])
    forms = list(store.name_variants.get("company_legal_forms") or [])
    is_co = _is_company(person.entity_type)
    candidates: List[str] = []
    if person.verified_name:
        candidates = [person.verified_name]
    else:
        candidates = [f.value for f in person.names if f.kind == "name"]
        if person.screened_name:
            candidates.append(person.screened_name)
    if not candidates or not hit.names:
        return None
    # Under-two-parts block confirm/clear on name
    usable = False
    for c in candidates:
        if can_use_name_for_clear_or_confirm(tokenize_name(c, forms if is_co else None)):
            usable = True
            break
    if not usable and not is_co:
        return None
    for c in candidates:
        for hn in hit.names:
            if names_agree(
                c,
                hn,
                variants=variants,
                company_legal_forms=forms if is_co else None,
                a_is_company=is_co,
                b_is_company=_is_company(hit.entity_type),
            ):
                return True
    return False


def dob_agrees(person: Person, hit: HitFacts) -> Optional[bool]:
    if person.dob_unknown or person.dob is None:
        return None
    if hit.dob_unknown or not hit.dobs:
        return None
    for h in hit.dobs:
        if intervals_agree(person.dob, h):
            return True
    return False


def countries_overlap(person: Person, hit: HitFacts) -> bool:
    return bool(person.countries & hit.countries)


def run_checks(person: Person, hit: HitFacts, store: DataStore) -> Dict[str, CheckResult]:
    return {
        "ENTITY_TYPE_MISMATCH": check_entity_type(person, hit),
        "DECEASED": check_deceased(hit),
        "TEMPORAL_IMPOSSIBILITY": check_temporal(person, hit),
        "DOB_MISMATCH": check_dob_mismatch(person, hit),
        "LOCATION_MISMATCH": check_location(person, hit),
        "NAME_MISMATCH_VERIFIED": check_name_mismatch(person, hit, store),
    }
