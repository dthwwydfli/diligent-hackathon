"""[B] Hit facts from structured fields (P5). Readers add free-text later."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from namesake.countries import parse_country_values
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
    countries, _opened = hit_countries_parsed(hit)
    return countries


def hit_countries_parsed(hit: Dict[str, Any]) -> Tuple[Set[str], bool]:
    """Return (mapped countries, open). Open when a place-like value does not map."""
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
    return parse_country_values(values)


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


def _snippet_names_country(snippet: str, countries: Set[str]) -> bool:
    """Whole-word country or demonym. Two-letter codes only when written in capitals.

    A lowercase "in" is the English word, not India.
    """
    from namesake.countries import CANON

    low = snippet.lower()
    for country in countries:
        if re.search(r"\b" + re.escape(country.lower()) + r"\b", low):
            return True
    for alias, canon in CANON.items():
        if canon not in countries or len(alias) < 3:
            continue
        if re.search(r"\b" + re.escape(alias) + r"\b", low):
            return True
    for match in re.finditer(r"\b[A-Z]{2}\b", snippet):
        canon = CANON.get(match.group(0).lower())
        if canon in countries:
            return True
    return False


def _snippet_age(snippet: str) -> Optional[int]:
    """One age in 16–110. Several different numbers → unknown, so we do not invent a birth year."""
    patterns = (
        r"(?:aged|age)\s+(\d{1,3})",
        r"(\d{1,3})\s*-\s*year\s*-?\s*old",
        r"(\d{1,3})\s+years?\s+old",
        r"\bwas\s+(\d{1,3})\b",
        r"\bthen\s+(\d{1,3})\b",
        r"\bat\s+the\s+age\s+of\s+(\d{1,3})",
        r"\bage\s+of\s+(\d{1,3})",
        r"\bat\s+(\d{1,3})\b",
        r",\s*(\d{2,3})\s*,",
    )
    found: List[int] = []
    for pattern in patterns:
        for match in re.finditer(pattern, snippet, re.I):
            number = int(next(group for group in match.groups() if group))
            if 16 <= number <= 110:
                found.append(number)
    unique = sorted(set(found))
    if len(unique) == 1:
        return unique[0]
    return None


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
        if not _snippet_names_country(snippet, countries):
            continue
        age = _snippet_age(snippet)
        llm_filled = False
        llm = getattr(store, "llm", None)
        if llm is not None:
            from namesake.llm import llm_fact

            payload = llm.second_opinion(snippet)
            if age is None:
                filled = llm_fact(payload, "age")
                if filled and str(filled).isdigit():
                    number = int(filled)
                    if 16 <= number <= 110:
                        age = number
                        llm_filled = True
        date_m = re.search(
            r"(January|February|March|April|May|June|July|August|September|October|November|December)"
            r"\s+(\d{4})|"
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+(\d{4})|"
            r"(\d{4})",
            snippet,
            re.I,
        )
        if age is not None and date_m:
            year = int(next(g for g in date_m.groups() if g and g.isdigit() and len(g) == 4))
            for y in age_at_date_years(age, year):
                out.append(
                    year_interval(
                        y,
                        certain=not llm_filled,
                        source=row.get("result_id") or "",
                    )
                )
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

    countries, countries_open = hit_countries_parsed(hit)
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
        for iv in profile_dobs:
            dobs.append(
                DateInterval(
                    iv.y_lo,
                    iv.m_lo,
                    iv.d_lo,
                    iv.y_hi,
                    iv.m_hi,
                    iv.d_hi,
                    certain=iv.certain,
                    source="profile",
                )
            )
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
        countries_open=countries_open,
        earliest_report=earliest,
        deceased_before_screen=deceased,
        deceased_source=deceased_source,
        evidence_ids=evidence,
        incorporation=incorporation,
    )
