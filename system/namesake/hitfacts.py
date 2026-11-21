"""[B] Hit facts from structured fields (P5). Readers add free-text later."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from namesake.countries import countries_from_values
from namesake.dates import DateInterval, age_at_date_years, parse_date, year_interval
from namesake.facts import HitFacts
from namesake.names import best_name_for_hit
from namesake.resources import load_json
from namesake.store import DataStore

_DATELINE = re.compile(
    r"According to .+?;\s*([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\s*:",
    re.IGNORECASE,
)


def listing_phrase(hit: Dict[str, Any]) -> str:
    data = load_json("listing_phrases.json")
    cat = hit.get("primary_category")
    if not cat:
        cats = hit.get("categories") or []
        cat = cats[0] if cats else None
    by_cat = data.get("by_category") or {}
    if cat and cat in by_cat:
        return by_cat[cat]
    return data.get("default") or "named on a watchlist"


def hit_countries(hit: Dict[str, Any]) -> Set[str]:
    values: List[Any] = []
    values.extend(hit.get("countries") or [])
    values.extend(hit.get("nationality") or [])
    values.extend(hit.get("citizenship") or [])
    if hit.get("place_of_birth"):
        values.append(hit["place_of_birth"])
    for addr in hit.get("addresses") or []:
        if isinstance(addr, str):
            values.append(addr)
        elif isinstance(addr, dict):
            values.append(addr.get("country") or addr.get("value") or str(addr))
    return countries_from_values(values)


def earliest_dated_report(profile_notes: Optional[str]) -> Optional[DateInterval]:
    """Exact form only (P5): According to …; <Month D, YYYY>: …"""
    if not profile_notes:
        return None
    earliest: Optional[DateInterval] = None
    for m in _DATELINE.finditer(profile_notes):
        text = f"{m.group(1)} {m.group(2)}, {m.group(3)}"
        iv = parse_date(text)
        if iv is None:
            continue
        if earliest is None or (iv.y_lo, iv.m_lo, iv.d_lo) < (
            earliest.y_lo,
            earliest.m_lo,
            earliest.d_lo,
        ):
            earliest = iv
    return earliest


def _query_forms(hit: Dict[str, Any]) -> List[str]:
    """Build candidate sorted-word queries from name + aliases (accent-folded first)."""
    import unicodedata

    from namesake.names import normalize_part

    forms: List[str] = []
    seen = set()
    candidates = []
    for key in ("best_matching_name", "name"):
        if hit.get(key):
            candidates.append(str(hit[key]))
    for alias in hit.get("aliases") or []:
        candidates.append(str(alias))
    bits = [hit.get("first_name"), hit.get("middle_name"), hit.get("last_name")]
    joined = " ".join(str(b) for b in bits if b)
    if joined.strip():
        candidates.append(joined)
    for name in candidates:
        text = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", name)
        # Fold accents before tokenising so Jérôme → Jerome, not J + r + me
        nk = unicodedata.normalize("NFKD", text)
        folded = "".join(ch for ch in nk if not unicodedata.combining(ch))
        raw_words = re.findall(r"[A-Za-z0-9]+", folded)
        words = sorted({normalize_part(w) for w in raw_words if len(normalize_part(w)) > 1})
        if not words:
            continue
        q = " ".join(words)
        if q not in seen:
            seen.add(q)
            forms.append(q)
    return forms


def accepted_snippet_years(
    store: DataStore, hit: Dict[str, Any], countries: Set[str]
) -> List[DateInterval]:
    """Accepted search results only when query is sorted name words + listing phrase + tied country."""
    phrase = listing_phrase(hit)
    out: List[DateInterval] = []
    rows = []
    for query in _query_forms(hit):
        rows.extend(store.query_to_search.get(query, []))
    # de-dupe by result_id
    seen_ids = set()
    unique_rows = []
    for row in rows:
        rid = row.get("result_id")
        if rid in seen_ids:
            continue
        seen_ids.add(rid)
        unique_rows.append(row)
    for row in unique_rows:
        snippet = row.get("snippet") or ""
        if phrase not in snippet:
            continue
        # must name a country tied to the hit
        tied = False
        for c in countries:
            if c.lower() in snippet.lower():
                tied = True
                break
            # also demonym / alias via reverse scan of CANON keys that map to c
            from namesake.countries import CANON

            for alias, canon in CANON.items():
                if canon == c and alias in snippet.lower():
                    tied = True
                    break
            if tied:
                break
        if not tied:
            continue
        # age + month/year in snippet → two birth years
        age_m = re.search(
            r"(?:aged|age)\s+(\d{1,3})"
            r"|(\d{1,3})-year-old"
            r"|(\d{1,3})\s+year[- ]old"
            r"|was\s+(\d{1,3})\b"
            r"|at the age of\s+(\d{1,3})"
            r"|age of\s+(\d{1,3})"
            r"|,\s*(\d{1,3}),\s*(?:who|a |an )",  # "Fiorani, 52, who was…"
            snippet,
            re.I,
        )
        date_m = re.search(
            r"(January|February|March|April|May|June|July|August|September|October|November|December)"
            r"\s+(\d{4})|"
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+(\d{4})|"
            r"(\d{4})",
            snippet,
            re.I,
        )
        if age_m and date_m:
            age = int(next(g for g in age_m.groups() if g))
            year = int(next(g for g in date_m.groups() if g and g.isdigit() and len(g) == 4))
            for y in age_at_date_years(age, year):
                out.append(year_interval(y, source=row.get("result_id") or ""))
    return out


def gather_hit_facts(store: DataStore, hit_id: str) -> HitFacts:
    hit = store.hits[hit_id]
    alert = store.alert_for_hit(hit_id) or {}
    is_company = (hit.get("entity_type") or "").lower() == "company"
    names: List[str] = []
    primary = best_name_for_hit(hit)
    if primary:
        names.append(primary)
    for alias in hit.get("aliases") or []:
        if alias and str(alias) not in names:
            names.append(str(alias))

    countries = hit_countries(hit)
    dobs: List[DateInterval] = []
    for raw in hit.get("dobs") or []:
        iv = parse_date(str(raw), source=hit_id)
        if iv:
            dobs.append(iv)

    incorporation = None
    dob_unknown = False
    if is_company:
        incorporation = dobs[0] if dobs else None
        # companies: only dobs is incorporation; profile "established" ignored for Time
    else:
        from namesake.readers import read_profile_first_paragraph

        profile_dobs, blocked = read_profile_first_paragraph(hit.get("profile_notes"))
        dobs.extend(profile_dobs)
        if blocked and not dobs:
            dob_unknown = True

    # Snippets only when dobs + profile birth empty (I1)
    if not is_company and not dobs and not dob_unknown:
        dobs.extend(accepted_snippet_years(store, hit, countries))

    earliest = earliest_dated_report(hit.get("profile_notes"))

    # Death: only deceased_date before screened_at (I4)
    deceased: Optional[bool] = None
    deceased_source = None
    screened_at = parse_date((alert or {}).get("screened_at"))
    if hit.get("deceased_date") and screened_at:
        dod = parse_date(hit["deceased_date"])
        if dod:
            deceased = (dod.y_hi, dod.m_hi, dod.d_hi) < (
                screened_at.y_lo,
                screened_at.m_lo,
                screened_at.d_lo,
            )
            deceased_source = hit_id
    elif hit.get("deceased_date"):
        deceased = None  # can't compare
    # life_status / prose → UNKNOWN (leave None)

    evidence = [hit_id]
    return HitFacts(
        hit_id=hit_id,
        alert_id=hit.get("alert_id") or "",
        entity_type=hit.get("entity_type") or "Individual",
        names=names,
        dobs=dobs,
        dob_unknown=dob_unknown,
        countries=countries,
        earliest_report=earliest,
        deceased_before_screen=deceased,
        deceased_source=deceased_source,
        evidence_ids=evidence,
        incorporation=incorporation,
    )
