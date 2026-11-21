"""P8 name comparison. Pure code. No LLM."""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, Iterable, List, Optional, Sequence, Set

from namesake.interpret import I12_PLACEHOLDER_EXTRA

# Policy-listed placeholders; I12 extends the set.
_POLICY_PLACEHOLDERS = frozenset({"NA", "N/A", "TEST", "UNKNOWN", "XXX", "NONE"})
PLACEHOLDERS = _POLICY_PLACEHOLDERS | {p.upper() for p in I12_PLACEHOLDER_EXTRA}


def _strip_accents(text: str) -> str:
    nk = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nk if not unicodedata.combining(ch))


def _strip_brackets(text: str) -> str:
    return re.sub(r"\[[^\]]*\]|\([^)]*\)|\{[^}]*\}", " ", text)


def normalize_part(part: str) -> str:
    part = _strip_accents(part)
    part = part.lower()
    part = re.sub(r"[^a-z0-9]", "", part)
    return part


def is_placeholder(token: str) -> bool:
    raw = token.strip()
    if not raw:
        return True
    upper = raw.upper()
    if upper in PLACEHOLDERS:
        return True
    # digits / punctuation only
    if re.fullmatch(r"[\d\W_]+", raw, flags=re.UNICODE):
        return True
    norm = normalize_part(raw)
    if not norm:
        return True
    if norm.upper() in PLACEHOLDERS:
        return True
    return False


def is_initial(token: str) -> bool:
    norm = normalize_part(token)
    return len(norm) == 1


def tokenize_name(
    name: Optional[str], company_legal_forms: Optional[Iterable[str]] = None
) -> List[str]:
    """Return distinct real name parts (lowercased, accent-stripped), excluding initials & placeholders.

    company_legal_forms: stripped only when the caller says this is a company name.
    """
    if not name:
        return []
    text = _strip_brackets(str(name))
    # Split on whitespace and common separators; keep letter runs.
    # Hyphens and apostrophes split AND stay joined, so Müller-Kägi
    # matches Müller and also Mullerkagi (P8: punctuation ignored;
    # parts written together or apart match).
    rough = re.split(r"[\s,;/|+]+", text)
    forms = {normalize_part(f) for f in (company_legal_forms or []) if f}
    parts: List[str] = []
    seen: Set[str] = set()

    def _add(tok: str) -> None:
        tok = tok.strip()
        if not tok or is_placeholder(tok):
            return
        if is_initial(tok):
            return
        norm = normalize_part(tok)
        if not norm:
            return
        if forms and norm in forms:
            return
        if norm in seen:
            return
        seen.add(norm)
        parts.append(norm)

    for tok in rough:
        pieces = [p for p in re.split(r"[-'’]+", tok) if p]
        if len(pieces) >= 2:
            for piece in pieces:
                _add(piece)
            _add("".join(pieces))
        else:
            _add(tok)
    return parts


def levenshtein(a: str, b: str) -> int:
    """Classic Levenshtein (POLICY: swapping two letters is two edits)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins = cur[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def edit_budget(shorter_len: int) -> int:
    if shorter_len < 4:
        return 0
    if shorter_len <= 6:
        return 1
    return 2


def build_variant_map(groups: Sequence[Sequence[str]]) -> Dict[str, Set[str]]:
    mapping: Dict[str, Set[str]] = {}
    for group in groups:
        norms = {normalize_part(x) for x in group if x}
        norms.discard("")
        for n in norms:
            mapping.setdefault(n, set()).update(norms)
    return mapping


def parts_match(
    a: str,
    b: str,
    variants: Optional[Dict[str, Set[str]]] = None,
) -> bool:
    """True when two parts match under P8 (identical, variant, join/split, or edit distance)."""
    if a == b:
        return True
    variants = variants or {}
    if b in variants.get(a, ()) or a in variants.get(b, ()):
        return True
    # Join/split: Abdulsalam matches Abdul + Salam (I2 / P8)
    # Handled at name level; single-part compare also allows concatenation.
    if a + b == a or b + a == b:
        return True
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    budget = edit_budget(len(shorter))
    if budget == 0:
        return shorter == longer
    return levenshtein(shorter, longer) <= budget


def _joined_covers(parts_a: List[str], parts_b: List[str], variants: Dict[str, Set[str]]) -> int:
    """Count join/split covers: one part equals concatenation of consecutive other parts (I2)."""
    covers = 0
    used_b: Set[int] = set()
    for pa in parts_a:
        for i in range(len(parts_b)):
            if i in used_b:
                continue
            # try concatenations of length 2+
            acc = ""
            idxs = []
            for j in range(i, len(parts_b)):
                if j in used_b:
                    break
                acc += parts_b[j]
                idxs.append(j)
                if len(idxs) >= 2 and acc == pa:
                    covers += 1
                    used_b.update(idxs)
                    break
                if len(acc) > len(pa):
                    break
    return covers


def names_agree(
    name_a: Optional[str],
    name_b: Optional[str],
    *,
    variants: Optional[Dict[str, Set[str]]] = None,
    company_legal_forms: Optional[Iterable[str]] = None,
    a_is_company: bool = False,
    b_is_company: bool = False,
) -> bool:
    """P8: names agree when ≥2 parts match, or every part of the shorter name matches."""
    forms_a = company_legal_forms if a_is_company else None
    forms_b = company_legal_forms if b_is_company else None
    pa = tokenize_name(name_a, forms_a)
    pb = tokenize_name(name_b, forms_b)
    if not pa or not pb:
        return False
    variants = variants or {}

    # Expand join/split into matching pairs
    matched_a: Set[int] = set()
    matched_b: Set[int] = set()

    # Direct part matches
    for i, a in enumerate(pa):
        for j, b in enumerate(pb):
            if j in matched_b:
                continue
            if parts_match(a, b, variants):
                matched_a.add(i)
                matched_b.add(j)
                break

    # Join/split: one side single token equals two+ on the other
    for i, a in enumerate(pa):
        if i in matched_a:
            continue
        for start in range(len(pb)):
            if start in matched_b:
                continue
            acc = ""
            idxs = []
            for j in range(start, len(pb)):
                if j in matched_b:
                    break
                acc += pb[j]
                idxs.append(j)
                if len(idxs) >= 2 and acc == a:
                    matched_a.add(i)
                    matched_b.update(idxs)
                    break
                if len(acc) > len(a):
                    break

    for j, b in enumerate(pb):
        if j in matched_b:
            continue
        for start in range(len(pa)):
            if start in matched_a:
                continue
            acc = ""
            idxs = []
            for i in range(start, len(pa)):
                if i in matched_a:
                    break
                acc += pa[i]
                idxs.append(i)
                if len(idxs) >= 2 and acc == b:
                    matched_b.add(j)
                    matched_a.update(idxs)
                    break
                if len(acc) > len(b):
                    break

    # Join counts as one part covering both — count distinct covers on the shorter side
    shorter = pa if len(pa) <= len(pb) else pb
    shorter_matched = matched_a if shorter is pa else matched_b
    if len(shorter_matched) == len(shorter):
        return True
    # At least two parts match
    return len(matched_a) >= 2 and len(matched_b) >= 2


def can_use_name_for_clear_or_confirm(parts: Sequence[str]) -> bool:
    """Individual with fewer than 2 real parts can be neither confirmed nor cleared on name."""
    return len(parts) >= 2


def best_name_for_hit(hit: dict) -> str:
    """Prefer best_matching_name, else name, else first/middle/last."""
    for key in ("best_matching_name", "name"):
        val = hit.get(key)
        if val and str(val).strip():
            return str(val).strip()
    bits = [hit.get("first_name"), hit.get("middle_name"), hit.get("last_name")]
    joined = " ".join(str(b) for b in bits if b)
    return joined.strip()
