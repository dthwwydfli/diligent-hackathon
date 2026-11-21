"""Issue 15: rewordings that drop entity tokens are discarded."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.twin.reword import preserves_tokens  # noqa: E402


def test_keeps_paraphrase_with_same_tokens() -> None:
    original = "SAMUEL DIAZ born 1988-10-03 in Nigeria"
    paraphrase = "Identity check for SAMUEL DIAZ, DOB 1988-10-03, document Nigeria"
    assert preserves_tokens(original, paraphrase)


def test_drops_paraphrase_missing_year() -> None:
    original = "SAMUEL DIAZ born 1988-10-03 in Nigeria"
    paraphrase = "SAMUEL DIAZ checked in Nigeria"
    assert not preserves_tokens(original, paraphrase)
