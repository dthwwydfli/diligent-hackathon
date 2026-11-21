"""Country / demonym / ISO code gazetteer. Data lives in data/countries.json (ODbL credit in README)."""

from __future__ import annotations

import json
import os
from typing import Dict, Optional, Set

_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "countries.json")


def _load():
    with open(_DATA_PATH, encoding="utf-8") as handle:
        raw = json.load(handle)
    not_countries = frozenset(x.lower() for x in raw.get("not_countries", []))
    canon: Dict[str, str] = {}
    for row in raw.get("countries", []):
        name = row["name"]
        canon[name.lower()] = name
        for alt in row.get("aliases", []):
            canon[str(alt).lower()] = name
    iso2 = frozenset(k for k in canon if len(k) == 2 and k.isalpha())
    return not_countries, canon, iso2


NOT_COUNTRIES, CANON, ISO2_CODES = _load()

# English words that collide with ISO2 / short aliases when lowercased.
_STOP = frozenset(
    {
        "by",
        "in",
        "to",
        "of",
        "on",
        "at",
        "or",
        "an",
        "as",
        "no",
        "id",  # "national ID" — not Indonesia unless written as country code alone
        "me",
        "my",
        "us",  # ambiguous; require uppercase US
        "am",
        "be",
        "do",
        "so",
        "if",
        "is",
    }
)


def canonical_country(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if "," in text:
        text = text.split(",")[-1].strip()
    key = text.lower()
    if key in NOT_COUNTRIES:
        return None
    # Two-letter codes: only when the source token is uppercase (US, GB, ID as code).
    if key in ISO2_CODES:
        if not text.isupper():
            return None
        if key in _STOP and not text.isupper():
            return None
    # Single short stop-words that are also aliases never match in lowercase prose.
    if key in _STOP and len(key) <= 2 and not text.isupper():
        return None
    return CANON.get(key)


def is_unmappable_place(raw: Optional[str]) -> bool:
    """True when a token looks place-like but is not in the gazetteer (I9)."""
    if raw is None:
        return False
    text = str(raw).strip()
    if not text:
        return False
    if "," in text:
        text = text.split(",")[-1].strip()
    key = text.lower()
    if key in NOT_COUNTRIES or key in CANON:
        # still unmappable if ISO2 blocked by case? treat mapped as mapped
        if canonical_country(text):
            return False
        if key in ISO2_CODES:
            return False
        if key in CANON and key not in ISO2_CODES:
            return False
    if canonical_country(text):
        return False
    letters = "".join(ch for ch in text if ch.isalpha() or ch.isspace())
    return len(letters.strip()) >= 3


def countries_from_values(values) -> Set[str]:
    out: Set[str] = set()
    for v in values or []:
        if isinstance(v, (list, tuple)):
            out |= countries_from_values(v)
            continue
        c = canonical_country(v)
        if c:
            out.add(c)
    return out


def extract_country_from_text(text: str) -> Optional[str]:
    """Prefer multi-word country names and 'from X' / 'in X' cues over bare ISO tokens."""
    import re

    # Explicit "from/in/issued in <Country…>"
    for m in re.finditer(
        r"\b(?:from|in|issued in|passport from|national ID from|ID from)\s+the\s+([A-Za-z][A-Za-z\- ]{1,40})",
        text,
        re.I,
    ):
        chunk = m.group(1).strip()
        # trim trailing junk words
        parts = chunk.split()
        for n in (3, 2, 1):
            if len(parts) >= n:
                cand = " ".join(parts[:n])
                c = canonical_country(cand)
                if c:
                    return c
    for m in re.finditer(
        r"\b(?:from|in|issued in|passport from)\s+([A-Za-z][A-Za-z\- ]{1,40})",
        text,
        re.I,
    ):
        chunk = m.group(1).strip()
        parts = chunk.split()
        for n in (3, 2, 1):
            if len(parts) >= n:
                cand = " ".join(parts[:n])
                c = canonical_country(cand)
                if c:
                    return c

    # Fall back: longest gazetteer alias present as a whole word / phrase
    best = None
    best_len = 0
    low = text.lower()
    for alias, name in CANON.items():
        if len(alias) < 3:
            continue
        if alias in low:
            # word-boundary-ish
            idx = low.find(alias)
            before = low[idx - 1] if idx > 0 else " "
            after = low[idx + len(alias)] if idx + len(alias) < len(low) else " "
            if before.isalnum() or after.isalnum():
                continue
            if len(alias) > best_len:
                best = name
                best_len = len(alias)
    return best
