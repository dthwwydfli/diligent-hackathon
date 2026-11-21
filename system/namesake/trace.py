"""Build per-hit trace JSON for the UI adapter. Never imported by the UI."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from namesake.checks import countries_overlap, dob_agrees, name_agrees
from namesake.countries import iso2_for_country
from namesake.dates import format_interval
from namesake.facts import CheckResult, HitFacts, Person
from namesake.store import DataStore


def build_engine_trace(
    store: DataStore,
    hit_id: str,
    alert: Dict[str, Any],
    persons: List[Person],
    hit: HitFacts,
    results: List[Tuple[str, str, List[str], Dict[str, Any], Person]],
    output_line: Dict[str, Any],
) -> Dict[str, Any]:
    """Full engine-side trace (SPEC §5.8b)."""
    found_via = _found_via(store, alert, persons)
    person_blocks, ghosts = _person_blocks(store, alert, persons)
    checks_dump = _checks_dump(results)
    missing = _missing_facts(output_line, results, hit, persons)
    return {
        "hit_id": hit_id,
        "alert_id": output_line.get("alert_id") or hit.alert_id,
        "screened_at": (alert or {}).get("screened_at"),
        "found_via": found_via,
        "persons": person_blocks,
        "ghosts": ghosts,
        "hit_facts": _hit_facts_dump(hit, store),
        "checks": checks_dump,
        "decision": output_line.get("decision"),
        "reason_code": output_line.get("reason_code"),
        "reason": output_line.get("reason"),
        "missing": missing,
        "output_line": dict(output_line),
    }


def build_case_page(
    store: DataStore,
    hit_id: str,
    alert: Dict[str, Any],
    persons: List[Person],
    hit: HitFacts,
    results: List[Tuple[str, str, List[str], Dict[str, Any], Person]],
    output_line: Dict[str, Any],
) -> Dict[str, Any]:
    """UI_SPEC §6 CasePage shape (what export_ui_data also emits)."""
    engine = build_engine_trace(store, hit_id, alert, persons, hit, results, output_line)
    primary = persons[0] if persons else None
    customer_name = _customer_display_name(primary, alert)
    customer_iso = _primary_iso(primary)
    hit_row = store.hits.get(hit_id) or {}
    alert_hits = store.alert_hits.get(alert.get("alert_id") or "", [])
    try:
        idx = alert_hits.index(hit_id) + 1
    except ValueError:
        idx = 1
    total = max(1, len(alert_hits) or 1)

    person_ui: List[Dict[str, Any]] = []
    for block in engine["persons"]:
        person_ui.append(block)

    profile = _profile_block(hit, hit_row, results)
    links, ladder = _links_and_ladder(persons, hit, results, output_line, store)
    status = _status_line(output_line, results)

    return {
        "hit_id": hit_id,
        "alert_id": output_line.get("alert_id") or hit.alert_id,
        "screened_at": (alert or {}).get("screened_at") or "",
        "hit_index": [idx, total],
        "customer_name": customer_name,
        "customer_country_iso2": customer_iso,
        "found_via": engine["found_via"],
        "persons": person_ui,
        "ghosts": engine["ghosts"],
        "profile": profile,
        "links": links,
        "ladder": ladder,
        "decision": output_line.get("decision"),
        "reason_code": output_line.get("reason_code"),
        "reason": output_line.get("reason"),
        "status": status,
        "missing": engine["missing"],
        "output_line": dict(output_line),
    }


def _found_via(
    store: DataStore, alert: Dict[str, Any], persons: List[Person]
) -> Dict[str, Any]:
    if alert.get("account_ref"):
        holders = store.account_holders.get(alert["account_ref"]) or []
        return {
            "kind": "account",
            "id": alert["account_ref"],
            "holders": len(holders),
            "fit": len(persons),
        }
    if alert.get("login_handle"):
        return {"kind": "login", "id": alert.get("login_handle"), "holders": None, "fit": len(persons)}
    if alert.get("email"):
        return {"kind": "email", "id": alert.get("email"), "holders": None, "fit": len(persons)}
    if persons:
        return {"kind": "search", "id": None, "holders": None, "fit": len(persons)}
    return {"kind": "none", "id": None, "holders": 0, "fit": 0}


def _customer_display_name(person: Optional[Person], alert: Dict[str, Any]) -> str:
    if person and person.verified_name:
        return person.verified_name
    if person and person.names:
        return str(person.names[0].value)
    screened = (alert or {}).get("customer") or {}
    return screened.get("name") or "Unknown customer"


def _primary_iso(person: Optional[Person]) -> Optional[str]:
    if not person:
        return None
    if person.verified_doc_country:
        return iso2_for_country(person.verified_doc_country)
    for name in sorted(person.countries):
        code = iso2_for_country(name)
        if code:
            return code
    return None


def _person_blocks(
    store: DataStore, alert: Dict[str, Any], persons: List[Person]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Fit persons + ghost holders who did not fit."""
    from namesake.names import build_variant_map
    from namesake.resolve import record_fits_screened

    blocks: List[Dict[str, Any]] = []
    ghosts: List[Dict[str, Any]] = []
    screened = (alert or {}).get("customer") or {}
    variants = build_variant_map(store.name_variants.get("groups") or [])
    forms = list(store.name_variants.get("company_legal_forms") or [])

    for i, person in enumerate(persons):
        label = f"Person {chr(ord('A') + i)}"
        merged_by = None
        if len(person.record_ids) > 1:
            merged_by = "same phone + DOB or same document number"
        name_display = _customer_display_name(person, alert)
        name_id = f"c{i}-name"
        verified = None
        facts: List[Dict[str, Any]] = []
        if person.dob is not None:
            facts.append(
                {
                    "id": f"c{i}-dob",
                    "display": f"Born {format_interval(person.dob)}",
                    "line": person.verified_source or "customer record",
                    "certain": person.dob.certain and not person.dob_unknown,
                }
            )
        for country in sorted(person.countries):
            facts.append(
                {
                    "id": f"c{i}-ctry-{iso2_for_country(country) or country}",
                    "display": country,
                    "line": "residence / nationality / document",
                    "certain": not person.countries_open,
                    "country_iso2": iso2_for_country(country),
                }
            )
        if person.has_approved_check and person.verified_source:
            provider = _provider_guess(store, person.verified_source)
            verified = {
                "provider": provider,
                "source": person.verified_source,
                "date": "",
                "facts": facts,
            }
        blocks.append(
            {
                "label": label,
                "fits": True,
                "records": list(person.record_ids),
                "merged_by": merged_by,
                "name": {
                    "id": name_id,
                    "display": name_display,
                    "country_iso2": _primary_iso(person),
                },
                "verified": verified,
                "facts": facts if verified is None else [],
            }
        )

    # Ghost holders from joint accounts that did not fit
    account_ref = alert.get("account_ref")
    if account_ref:
        fitted = {rid for p in persons for rid in p.record_ids}
        holders = store.account_holders.get(account_ref) or []
        ghost_i = 0
        for cid in holders:
            if cid in fitted:
                continue
            rec = store.customers.get(cid) or {}
            fits = record_fits_screened(rec, screened, variants, forms)
            if fits:
                continue
            dob = rec.get("dob") or "?"
            ghosts.append(
                {
                    "label": f"Person {chr(ord('B') + ghost_i)}",
                    "line": f"other holder, born {dob}, no fit",
                }
            )
            ghost_i += 1
    return blocks, ghosts


def _provider_guess(store: DataStore, source_id: str) -> str:
    if source_id.startswith("KYC-"):
        for check in store.kyc_checks:
            if check.get("check_id") == source_id:
                return check.get("provider") or "KYC provider"
    if source_id.startswith("NOTE-"):
        return "Onboarding note"
    return "Identity check"


def _hit_facts_dump(hit: HitFacts, store: DataStore) -> Dict[str, Any]:
    hit_row = store.hits.get(hit.hit_id) or {}
    return {
        "names": list(hit.names),
        "dobs": [
            {
                "value": format_interval(d),
                "source": d.source,
                "certain": d.certain,
            }
            for d in hit.dobs
        ],
        "countries": sorted(hit.countries),
        "country_iso2": [iso2_for_country(c) for c in sorted(hit.countries)],
        "dob_unknown": hit.dob_unknown,
        "entity_type": hit.entity_type,
        "category": (hit_row.get("primary_category") or (hit_row.get("categories") or [None])[0]),
        "match_score": hit_row.get("match_score"),
        "deceased_before_screen": hit.deceased_before_screen,
    }


def _checks_dump(
    results: List[Tuple[str, str, List[str], Dict[str, Any], Person]],
) -> List[Dict[str, Any]]:
    if not results:
        return []
    ctx = results[0][3] or {}
    checks: Dict[str, CheckResult] = ctx.get("checks") or {}
    out = []
    for name, cr in checks.items():
        out.append(
            {
                "name": name,
                "value": cr.value,
                "reason_code": cr.reason_code,
                "evidence": list(cr.evidence),
            }
        )
    return out


def _missing_facts(
    output_line: Dict[str, Any],
    results: List[Tuple[str, str, List[str], Dict[str, Any], Person]],
    hit: HitFacts,
    persons: List[Person],
) -> List[Dict[str, str]]:
    if output_line.get("decision") != "REVIEW":
        return []
    missing: List[Dict[str, str]] = []
    if hit.dob_unknown or not hit.dobs:
        missing.append({"side": "profile", "display": "No birth date found"})
    person = persons[0] if persons else None
    if person and (person.dob_unknown or person.dob is None):
        missing.append({"side": "customer", "display": "No customer birth date found"})
    if not missing and results:
        ctx = results[0][3] or {}
        if ctx.get("name_ok") is None:
            missing.append({"side": "customer", "display": "Name cannot be settled"})
        elif ctx.get("dob_ok") is None:
            missing.append({"side": "profile", "display": "Date of birth cannot be compared"})
    return missing


def _profile_block(
    hit: HitFacts,
    hit_row: Dict[str, Any],
    results: List[Tuple[str, str, List[str], Dict[str, Any], Person]],
) -> Dict[str, Any]:
    del results
    cat = hit_row.get("primary_category") or ((hit_row.get("categories") or ["Watchlist"])[0])
    name = hit.names[0] if hit.names else (hit_row.get("name") or "Listed profile")
    iso = None
    for c in sorted(hit.countries):
        iso = iso2_for_country(c)
        if iso:
            break
    facts: List[Dict[str, Any]] = []
    if hit.dobs:
        years = [format_interval(d) for d in hit.dobs]
        display = " or ".join(dict.fromkeys(years))
        src = hit.dobs[0].source or "dobs field"
        line = "dobs field" if not src.startswith("SR-") and src != "profile" else src
        if src.startswith("SR-"):
            line = f"search snippet · {src}"
        elif src == "profile":
            line = "profile sentence"
        facts.append(
            {
                "id": "h-dob",
                "display": f"Born {display}",
                "line": line,
                "certain": all(d.certain for d in hit.dobs) and not hit.dob_unknown,
                "source": src if src.startswith("SR-") else None,
            }
        )
    for country in sorted(hit.countries):
        facts.append(
            {
                "id": f"h-ctry-{iso2_for_country(country) or country}",
                "display": country,
                "line": "nationality on profile",
                "certain": True,
                "country_iso2": iso2_for_country(country),
            }
        )
    sources = []
    for d in hit.dobs:
        if d.source and d.source.startswith("SR-"):
            sources.append(
                {
                    "id": "h-src",
                    "label": "News result",
                    "note": "same role + country",
                    "supports": "h-dob",
                }
            )
            break
    return {
        "category": cat or "Watchlist",
        "score": hit_row.get("match_score"),
        "name": {"id": "h-name", "display": name, "country_iso2": iso},
        "facts": facts,
        "sources": sources,
    }


def _links_and_ladder(
    persons: List[Person],
    hit: HitFacts,
    results: List[Tuple[str, str, List[str], Dict[str, Any], Person]],
    output_line: Dict[str, Any],
    store: DataStore,
) -> Tuple[List[List[str]], List[Dict[str, Any]]]:
    person = persons[0] if persons else None
    ctx = (results[0][3] if results else {}) or {}
    checks: Dict[str, CheckResult] = ctx.get("checks") or {}
    n_ok = ctx.get("name_ok")
    d_ok = ctx.get("dob_ok")
    if n_ok is None and person is not None:
        n_ok = name_agrees(person, hit, store)
    if d_ok is None and person is not None:
        d_ok = dob_agrees(person, hit)
    overlap = countries_overlap(person, hit) if person else False

    links: List[List[str]] = []
    if person is not None:
        name_outcome = _agree_outcome(n_ok)
        links.append(["c0-name", "h-name", name_outcome])
        if person.dob is not None or hit.dobs or hit.dob_unknown:
            dob_outcome = _agree_outcome(d_ok)
            if hit.dob_unknown or not hit.dobs:
                dob_outcome = "review"
            links.append(["c0-dob", "h-dob", dob_outcome])
        if person.countries and hit.countries:
            loc = checks.get("LOCATION_MISMATCH")
            if loc and loc.is_true and not (n_ok is True and d_ok is True):
                loc_outcome = "clear"
            elif overlap:
                loc_outcome = "match"
            elif loc and loc.is_unknown:
                loc_outcome = "review"
            else:
                loc_outcome = "clear" if (person.countries and hit.countries) else "review"
            c_iso = iso2_for_country(sorted(person.countries)[0]) or "x"
            h_iso = iso2_for_country(sorted(hit.countries)[0]) or "x"
            links.append([f"c0-ctry-{c_iso}", f"h-ctry-{h_iso}", loc_outcome])
        for d in hit.dobs:
            if d.source and d.source.startswith("SR-"):
                links.append(["h-src", "h-dob", "source"])
                break

    def chip(val: Optional[bool], check: Optional[CheckResult]) -> str:
        if check and check.is_true:
            return "contradicts"
        if check and check.is_unknown:
            return "unknown"
        if val is True:
            return "agrees"
        if val is False:
            return "unknown"
        return "unknown"

    type_cr = checks.get("ENTITY_TYPE_MISMATCH")
    time_cr = checks.get("TEMPORAL_IMPOSSIBILITY") or checks.get("DECEASED")
    dob_cr = checks.get("DOB_MISMATCH")
    loc_cr = checks.get("LOCATION_MISMATCH")
    name_cr = checks.get("NAME_MISMATCH_VERIFIED")

    decision = output_line.get("decision")
    if decision == "SAME_ENTITY":
        result_chip = "Same"
    elif decision == "DIFFERENT_ENTITY":
        result_chip = "Cleared"
    else:
        result_chip = "Review"

    ladder = [
        {
            "check": "Type",
            "phrase": _type_phrase(person, hit),
            "outcome": "contradicts" if type_cr and type_cr.is_true else "agrees",
            "link_ids": ["c0-name", "h-name"],
        },
        {
            "check": "Time",
            "phrase": _time_phrase(time_cr, hit),
            "outcome": chip(None, time_cr),
            "link_ids": [],
        },
        {
            "check": "Birth date",
            "phrase": _dob_phrase(person, hit, d_ok),
            "outcome": "contradicts"
            if dob_cr and dob_cr.is_true
            else ("agrees" if d_ok is True else "unknown"),
            "link_ids": ["c0-dob", "h-dob"],
        },
        {
            "check": "Country",
            "phrase": _country_phrase(person, hit, overlap),
            "outcome": "contradicts"
            if loc_cr and loc_cr.is_true and not (n_ok is True and d_ok is True)
            else ("agrees" if overlap else "unknown"),
            "link_ids": [lnk[0] for lnk in links if "ctry" in lnk[0]],
        },
        {
            "check": "Name",
            "phrase": _name_phrase(n_ok, name_cr),
            "outcome": "contradicts"
            if name_cr and name_cr.is_true
            else ("agrees" if n_ok is True else "unknown"),
            "link_ids": ["c0-name", "h-name"],
        },
        {
            "check": "Result",
            "phrase": output_line.get("reason_code") or "",
            "outcome": "result",
            "result_chip": result_chip,
            "link_ids": [],
        },
    ]
    return links, ladder


def _agree_outcome(val: Optional[bool]) -> str:
    if val is True:
        return "match"
    if val is False:
        return "clear"
    return "review"


def _type_phrase(person: Optional[Person], hit: HitFacts) -> str:
    p = person.entity_type if person else "unknown"
    return f"{p} · {hit.entity_type}"


def _time_phrase(cr: Optional[CheckResult], hit: HitFacts) -> str:
    if cr and cr.is_true:
        return cr.reason_code or "Temporal contradiction"
    if hit.earliest_report is None:
        return "No dated report"
    return "Timed report present"


def _dob_phrase(person: Optional[Person], hit: HitFacts, d_ok: Optional[bool]) -> str:
    if person and person.dob and hit.dobs:
        return f"{format_interval(person.dob)} vs {format_interval(hit.dobs[0])}"
    if d_ok is True:
        return "Dates agree"
    if not hit.dobs:
        return "No hit birth date"
    return "Cannot compare"


def _country_phrase(person: Optional[Person], hit: HitFacts, overlap: bool) -> str:
    left = ", ".join(sorted(person.countries)) if person and person.countries else "—"
    right = ", ".join(sorted(hit.countries)) if hit.countries else "—"
    if overlap:
        return f"{left} · {right}"
    return f"{left} · {right}"


def _name_phrase(n_ok: Optional[bool], name_cr: Optional[CheckResult]) -> str:
    if name_cr and name_cr.is_true:
        return "Verified name disagrees"
    if n_ok is True:
        return "Parts agree"
    if n_ok is False:
        return "Names disagree"
    return "Cannot compare"


def _status_line(
    output_line: Dict[str, Any],
    results: List[Tuple[str, str, List[str], Dict[str, Any], Person]],
) -> Dict[str, str]:
    decision = output_line.get("decision")
    if decision == "REVIEW":
        return {"kind": "none", "text": ""}
    ctx = (results[0][3] if results else {}) or {}
    checks: Dict[str, CheckResult] = ctx.get("checks") or {}
    for cr in checks.values():
        if cr.is_unknown and decision == "DIFFERENT_ENTITY":
            return {"kind": "blocked", "text": f"Clearance blocked: {cr.name} uncertain"}
    if decision in {"SAME_ENTITY", "DIFFERENT_ENTITY"}:
        return {"kind": "certain", "text": "Every fact used is certain"}
    return {"kind": "none", "text": ""}
