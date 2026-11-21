"""Output schema mirrors vendor/organiser/output.schema.json."""

from __future__ import annotations

import pytest

from namesake.schema import dumps_line, make_line, validate_line


def test_valid_review_line() -> None:
    row = make_line(
        "H-ABCDEF",
        "A-123456",
        "REVIEW",
        "INSUFFICIENT_DATA",
        None,
        "Needs a human look.",
        ["H-ABCDEF"],
    )
    assert validate_line(row) is None
    assert '"hit_id":"H-ABCDEF"' in dumps_line(row)


def test_reason_code_must_match_decision() -> None:
    """Schema allOf: DOB_MISMATCH belongs only to DIFFERENT_ENTITY."""
    row = make_line(
        "H-ABCDEF",
        "A-123456",
        "REVIEW",
        "DOB_MISMATCH",
        None,
        "Bad pairing.",
        [],
    )
    assert validate_line(row) is not None


def test_customer_record_patterns() -> None:
    ok = make_line(
        "H-ABCDEF",
        "A-123456",
        "SAME_ENTITY",
        "NAME_DOB_MATCH",
        "CUS-000001",
        "Match.",
        ["CUS-000001"],
    )
    assert validate_line(ok) is None
    bad = dict(ok)
    bad["customer_record_id"] = "CUS-1"
    assert validate_line(bad) is not None


def test_dumps_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        dumps_line({"hit_id": "bad"})
