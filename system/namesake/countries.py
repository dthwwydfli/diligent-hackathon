"""Country / demonym / ISO code gazetteer. Data lives in data/countries.json (ODbL credit in README)."""

from __future__ import annotations

import json
import os
import re
import unicodedata
from typing import Dict, Iterable, Optional, Set, Tuple

_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "countries.json")
_TAG = re.compile(r"\s*\[[^\]]*\]\s*$")


def _fold(text: str) -> str:
    nk = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nk if not unicodedata.combining(ch))


def _load():
    with open(_DATA_PATH, encoding="utf-8") as handle:
        raw = json.load(handle)
    not_countries = frozenset(x.lower() for x in raw.get("not_countries", []))
    canon: Dict[str, str] = {}
    for row in raw.get("countries", []):
        name = row["name"]
        for key in (name.lower(), _fold(name).lower()):
            canon[key] = name
        for alt in row.get("aliases", []):
            text = str(alt)
            for key in (text.lower(), _fold(text).lower()):
                canon[key] = name
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

# Canonical English name → lowercase ISO-2 (for UI flags).
# Stop-words (us, at, in, …) still block those tokens in prose, but the
# code itself is the right flag for that country.
_NAME_TO_ISO2: Dict[str, str] = {}
for _alias, _name in CANON.items():
    if len(_alias) == 2 and _alias.isalpha():
        _NAME_TO_ISO2.setdefault(_name, _alias.lower())


def _prepare(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    text = _TAG.sub("", text).strip()
    if "," in text:
        text = text.split(",")[-1].strip()
        text = _TAG.sub("", text).strip()
    return text or None


def canonical_country(raw: Optional[str]) -> Optional[str]:
    text = _prepare(raw)
    if text is None:
        return None
    key = text.lower()
    folded = _fold(key)
    if key in NOT_COUNTRIES or folded in NOT_COUNTRIES:
        return None
    # Two-letter codes: only when the source token is uppercase (US, GB, ID as code).
    if (key in ISO2_CODES or folded in ISO2_CODES) and not text.isupper():
        return None
    if key in _STOP and len(key) <= 2 and not text.isupper():
        return None
    return CANON.get(key) or CANON.get(folded)


def iso2_for_country(name: Optional[str]) -> Optional[str]:
    """Lowercase ISO-2 for a canonical country name, or None."""
    if not name:
        return None
    got = _NAME_TO_ISO2.get(name)
    if got:
        return got
    canon = canonical_country(name)
    if canon:
        return _NAME_TO_ISO2.get(canon)
    key = str(name).strip().lower()
    if len(key) == 2 and key.isalpha() and key in ISO2_CODES:
        return key
    return None


def is_unmappable_place(raw: Optional[str]) -> bool:
    """True when a token looks place-like but is not in the gazetteer (I9)."""
    text = _prepare(raw)
    if text is None:
        return False
    key = text.lower()
    folded = _fold(key)
    if key in NOT_COUNTRIES or folded in NOT_COUNTRIES:
        return False
    if canonical_country(text):
        return False
    if key in CANON or folded in CANON:
        # Mapped in the table but blocked by case (e.g. lowercase "us").
        return False
    letters = "".join(ch for ch in text if ch.isalpha() or ch.isspace())
    return len(letters.strip()) >= 3


def countries_from_values(values) -> Set[str]:
    mapped, _opened = parse_country_values(values)
    return mapped


def parse_country_values(values: Optional[Iterable]) -> Tuple[Set[str], bool]:
    """Map country-like values. Open the set when a place-like token does not map (I9)."""
    out: Set[str] = set()
    opened = False
    for v in values or []:
        if isinstance(v, (list, tuple)):
            mapped, child_open = parse_country_values(v)
            out |= mapped
            opened = opened or child_open
            continue
        if isinstance(v, dict):
            piece = v.get("country") or v.get("value") or ""
            mapped, child_open = parse_country_values([piece] if piece else [])
            out |= mapped
            opened = opened or child_open
            continue
        text = _prepare(v)
        if text is None:
            continue
        key = text.lower()
        folded = _fold(key)
        if key in NOT_COUNTRIES or folded in NOT_COUNTRIES:
            continue
        c = canonical_country(text)
        if c:
            out.add(c)
            continue
        if is_unmappable_place(text):
            opened = True
    return out, opened


def extract_country_from_text(text: str) -> Optional[str]:
    """Prefer multi-word country names and 'from X' / 'in X' cues over bare ISO tokens."""
    import re as _re

    # Explicit "from/in/issued in <Country…>"
    for m in _re.finditer(
        r"\b(?:from|in|issued in|passport from|national ID from|ID from)\s+the\s+([A-Za-z][A-Za-z\- ]{1,40})",
        text,
        _re.I,
    ):
        chunk = m.group(1).strip()
        parts = chunk.split()
        for n in (3, 2, 1):
            if len(parts) >= n:
                cand = " ".join(parts[:n])
                c = canonical_country(cand)
                if c:
                    return c
    for m in _re.finditer(
        r"\b(?:from|in|issued in|passport from)\s+([A-Za-z][A-Za-z\- ]{1,40})",
        text,
        _re.I,
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
    low = _fold(text.lower())
    for alias, name in CANON.items():
        if len(alias) < 3:
            continue
        if alias in low:
            idx = low.find(alias)
            before = low[idx - 1] if idx > 0 else " "
            after = low[idx + len(alias)] if idx + len(alias) < len(low) else " "
            if before.isalnum() or after.isalnum():
                continue
            if len(alias) > best_len:
                best = name
                best_len = len(alias)
    return best
