"""[C] Wording-independent token readers. Safe-without-LLM rules marked explicitly."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from namesake.countries import canonical_country, extract_country_from_text, is_unmappable_place
from namesake.dates import (
    DateInterval,
    age_at_date_years,
    find_dates,
    parse_date,
    same_calendar_day,
    year_interval,
)
from namesake.resources import load_json


@dataclass
class NoteExtraction:
    verified_name: Optional[str] = None
    dob: Optional[DateInterval] = None
    document_country: Optional[str] = None
    approved: Optional[bool] = None  # True/False/None(unknown polarity)
    countries_lived: List[str] = field(default_factory=list)
    open_country_set: bool = False
    certain: bool = False


def _polarity(text: str) -> Optional[bool]:
    data = load_json("polarity.json")
    low = text.lower()
    neg = any(n in low for n in data.get("negative") or [])
    pos = any(p in low for p in data.get("positive") or [])
    if neg:
        return False
    if pos:
        return True
    return None


_YEAR = re.compile(r"\b((?:19|20)\d{2})\b")


def _uppercase_name(text: str) -> Optional[str]:
    """Longest run of uppercase words. Accented capitals count; one word does not."""
    words = re.findall(r"[^\W\d_]+", text, flags=re.UNICODE)
    run: List[str] = []
    best: List[str] = []
    for word in words:
        letters = [ch for ch in word if ch.isalpha()]
        if len(letters) >= 2 and all(ch.isupper() for ch in letters):
            run.append(word)
            continue
        if len(run) > len(best):
            best = run
        run = []
    if len(run) > len(best):
        best = run
    if len(best) < 2:
        return None
    return " ".join(word.capitalize() for word in best)


def read_kyc_note(text: str, created_at: str) -> NoteExtraction:
    """KYC-channel note. Tokens, not sentence templates: uppercase run, any other date, a country."""
    out = NoteExtraction()
    pol = _polarity(text)
    out.approved = pol

    created = parse_date(created_at)
    dates = find_dates(text)
    check_date = None
    dob = None
    if created:
        for iv in dates:
            if same_calendar_day(iv, created) or (
                iv.y_lo == created.y_lo and iv.m_lo == created.m_lo and iv.d_lo == created.d_lo
            ):
                check_date = iv
                break
        for iv in dates:
            if check_date is not None and (
                iv.y_lo == check_date.y_lo
                and iv.m_lo == check_date.m_lo
                and iv.d_lo == check_date.d_lo
            ):
                continue
            dob = iv
            break
    elif dates:
        dob = dates[0]

    out.document_country = extract_country_from_text(text)
    out.verified_name = _uppercase_name(text)
    out.dob = dob

    if pol is False:
        out.approved = False
        out.certain = True
        return out

    if pol is not True:
        # I10: unclear polarity — not an approved check
        out.approved = None
        out.certain = False
        return out

    out.approved = True
    if (
        check_date is not None
        and out.dob is not None
        and out.document_country is not None
        and out.verified_name is not None
    ):
        out.certain = True
    elif out.dob is not None and out.verified_name is not None:
        out.certain = out.dob.certain
    else:
        out.certain = False
    return out


def read_residence_note(text: str) -> NoteExtraction:
    """Country + year ⇒ lived there. Unmappable place opens country set (I9)."""
    out = NoteExtraction()
    low = text.lower()
    years = _YEAR.findall(text)
    lived_cue = any(
        cue in low
        for cue in ("lived", "live in", "resided", "resident", "based in", "moved to", "from ")
    )
    tokens = re.findall(r"[A-Za-z][A-Za-z\-']+", text)
    found = False
    for i, tok in enumerate(tokens):
        if i + 1 < len(tokens):
            pair = f"{tok} {tokens[i + 1]}"
            c = canonical_country(pair)
            if c:
                out.countries_lived.append(c)
                found = True
                continue
        c = canonical_country(tok)
        if c:
            out.countries_lived.append(c)
            found = True
        elif (
            lived_cue
            and years
            and tok[0].isupper()
            and is_unmappable_place(tok)
            and tok.lower()
            not in {
                "i",
                "the",
                "a",
                "an",
                "in",
                "on",
                "at",
                "to",
                "from",
                "customer",
                "client",
                "note",
            }
        ):
            out.open_country_set = True
    if years and found:
        out.certain = True
    return out


def read_profile_first_paragraph(text: Optional[str]) -> Tuple[List[DateInterval], bool]:
    """Birth facts from first paragraph. Returns (dobs, blocked_snippets)."""
    if not text:
        return [], False
    para = text.split("\n\n")[0] if "\n\n" in text else text[:800]
    dobs: List[DateInterval] = []
    blocked = False
    m = re.search(r"\bborn\s+in\s+(\d{4})\b", para, re.I)
    if m:
        iv = parse_date(m.group(1))
        if iv:
            dobs.append(iv)
        else:
            blocked = True
    m = re.search(r"\bborn\s+on\s+([^.;\n]+)", para, re.I)
    if m:
        iv = parse_date(m.group(1).strip())
        if iv:
            dobs.append(iv)
        else:
            blocked = True
    age_m = re.search(
        r"(?:aged|age)\s+(\d{1,3})"
        r"|(\d{1,3})-year-old"
        r"|(\d{1,3})\s+year[- ]old"
        r"|was\s+(\d{1,3})\b"
        r"|reached the age of\s+(\d{1,3})"
        r"|age of\s+(\d{1,3})",
        para,
        re.I,
    )
    date_m = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+\d{1,2},?\s+(\d{4})|"
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(\d{4})",
        para,
        re.I,
    )
    if age_m and date_m:
        age = int(next(g for g in age_m.groups() if g))
        year = int(next(g for g in date_m.groups() if g and str(g).isdigit() and len(str(g)) == 4))
        for y in age_at_date_years(age, year):
            dobs.append(year_interval(y))
    elif re.search(r"\bborn\b", para, re.I) and not dobs:
        blocked = True
    return dobs, blocked
