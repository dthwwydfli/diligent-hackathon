"""Second implementation of POLICY.md decisions. No imports from system.namesake."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple


def _year(raw: Optional[str]) -> Optional[int]:
    if not raw:
        return None
    text = str(raw).strip()
    if len(text) >= 4 and text[:4].isdigit():
        return int(text[:4])
    # DD/MM/YYYY
    parts = text.replace("-", "/").split("/")
    if len(parts) == 3 and parts[-1].isdigit() and len(parts[-1]) == 4:
        return int(parts[-1])
    return None


def _years_close(a: int, b: int) -> bool:
    return abs(a - b) <= 1


def decide_from_facts(
    *,
    customer_entity: str,
    hit_entity: str,
    customer_dob_year: Optional[int],
    hit_dob_years: List[int],
    customer_countries: Set[str],
    hit_countries: Set[str],
    name_agrees: bool,
    verified_name_agrees: Optional[bool],
    countries_open: bool,
    deceased_before_screen: Optional[bool],
    under_16: bool,
    company_after_report: bool,
) -> Tuple[str, str]:
    """Return (decision, reason_code) from already-extracted facts.

    Written from POLICY.md P6/P7 only — not from the engine source.
    """
    cust_co = (customer_entity or "").lower() == "company"
    hit_co = (hit_entity or "").lower() == "company"
    if cust_co != hit_co:
        return "DIFFERENT_ENTITY", "ENTITY_TYPE_MISMATCH"
    if deceased_before_screen is True:
        return "DIFFERENT_ENTITY", "DECEASED"
    if under_16 or company_after_report:
        return "DIFFERENT_ENTITY", "TEMPORAL_IMPOSSIBILITY"

    dob_agree = False
    dob_mismatch = False
    if customer_dob_year is not None and hit_dob_years:
        dob_agree = customer_dob_year in hit_dob_years
        # mismatch: every hit year contradicted by >1 year gap
        dob_mismatch = all(not _years_close(customer_dob_year, hy) for hy in hit_dob_years)
        if dob_agree:
            dob_mismatch = False

    if dob_mismatch:
        return "DIFFERENT_ENTITY", "DOB_MISMATCH"

    if verified_name_agrees is False:
        return "DIFFERENT_ENTITY", "NAME_MISMATCH_VERIFIED"

    name_dob_agree = name_agrees and dob_agree and not cust_co and not hit_co
    loc_mismatch = (
        (not countries_open)
        and bool(customer_countries)
        and bool(hit_countries)
        and customer_countries.isdisjoint(hit_countries)
    )
    if loc_mismatch and not name_dob_agree:
        return "DIFFERENT_ENTITY", "LOCATION_MISMATCH"
    if loc_mismatch and name_dob_agree:
        return "REVIEW", "INSUFFICIENT_DATA"

    overlap = bool(customer_countries & hit_countries)
    if hit_co or cust_co:
        if name_agrees and overlap:
            return "SAME_ENTITY", "NAME_LOCATION_MATCH"
        return "REVIEW", "INSUFFICIENT_DATA"

    if name_dob_agree:
        if overlap:
            return "SAME_ENTITY", "NAME_DOB_LOCATION_MATCH"
        return "SAME_ENTITY", "NAME_DOB_MATCH"

    return "REVIEW", "INSUFFICIENT_DATA"


def compare_outputs(
    engine_rows: List[Dict[str, Any]], checker_rows: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Return disagreements {hit_id, engine, checker}."""
    by_e = {r["hit_id"]: r for r in engine_rows}
    by_c = {r["hit_id"]: r for r in checker_rows}
    out = []
    for hid in sorted(set(by_e) | set(by_c)):
        e = by_e.get(hid, {})
        c = by_c.get(hid, {})
        if (e.get("decision"), e.get("reason_code")) != (c.get("decision"), c.get("reason_code")):
            out.append(
                {
                    "hit_id": hid,
                    "engine": (e.get("decision"), e.get("reason_code")),
                    "checker": (c.get("decision"), c.get("reason_code")),
                }
            )
    return out
