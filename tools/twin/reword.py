"""Rewording invariance helpers. Keep only paraphrases that preserve entity tokens."""

from __future__ import annotations

import re
from typing import Set


def entity_tokens(text: str) -> Set[str]:
    """Countries (title-ish), ISO dates, years, ages, UPPER names — coarse token set."""
    tokens: Set[str] = set()
    for m in re.finditer(r"\b\d{4}-\d{2}-\d{2}\b", text):
        tokens.add(m.group(0))
    for m in re.finditer(r"\b(?:19|20)\d{2}\b", text):
        tokens.add(m.group(0))
    for m in re.finditer(r"\b\d{1,3}-year-old\b", text, re.I):
        tokens.add(m.group(0).lower())
    for m in re.finditer(r"\b[A-Z]{2,}(?:\s+[A-Z]{2,})+\b", text):
        tokens.add(m.group(0))
    return tokens


def preserves_tokens(original: str, paraphrase: str) -> bool:
    """Discard a rewording that drops any entity token from the original."""
    return entity_tokens(original).issubset(entity_tokens(paraphrase))
