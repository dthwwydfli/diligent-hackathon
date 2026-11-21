"""Each register row is a named constant (SPEC §5 / I1–I13)."""

from __future__ import annotations

from namesake import interpret as I


def test_register_constants_exist() -> None:
    """SPEC §5: every I-row is a named constant."""
    assert I.I1_HIT_DOB_UNION.startswith("I1")
    assert I.I2_JOINED_SPLIT_ONE_PART.startswith("I2")
    assert I.I3_VERIFIED_NAME_PREFERRED.startswith("I3")
    assert I.I4_DEATH_PROSE_UNKNOWN.startswith("I4")
    assert I.I5_MOST_RECENT_APPROVED.startswith("I5")
    assert I.I6_CONFLICTING_DECLARED_DOB.startswith("I6")
    assert I.I7_MULTI_PERSON_SAME_DECISION.startswith("I7")
    assert I.I8_SHORTEST_PROOF_CODE.startswith("I8")
    assert I.I9_UNMAPPABLE_PLACE_OPENS.startswith("I9")
    assert I.I10_UNCLEAR_POLARITY.startswith("I10")
    assert I.I11_NO_RECORD_NULL.startswith("I11")
    assert "NULL" in I.I12_PLACEHOLDER_EXTRA
    assert "DUMMY" in I.I12_PLACEHOLDER_EXTRA
    assert I.I13_SNIPPET_YEAR_UNION.startswith("I13")
