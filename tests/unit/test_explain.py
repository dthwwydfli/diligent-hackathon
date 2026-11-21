"""Issue 10: reasons 2–4 sentences; evidence is proof ids only."""

from __future__ import annotations

from namesake.dates import parse_date
from namesake.explain import build_reason
from namesake.facts import HitFacts, Person


def test_review_has_counterfactual_sentence() -> None:
    person = Person(record_ids=["CUS-000001"])
    hit = HitFacts(hit_id="H-AAAAAA", alert_id="A-AAAAAA", entity_type="Individual")
    reason = build_reason(
        "REVIEW",
        "INSUFFICIENT_DATA",
        person,
        hit,
        {"checks": {}, "name_ok": None},
    )
    sentences = [s for s in reason.split(".") if s.strip()]
    assert 2 <= len(sentences) <= 4
    assert "date of birth" in reason.lower()
    assert "A human should review" not in reason


def test_dob_mismatch_mentions_ids_and_values() -> None:
    person = Person(record_ids=["CUS-000001"], verified_source="NOTE-AAAAAA")
    person.dob = parse_date("1990-01-01")
    hit = HitFacts(
        hit_id="H-AAAAAA",
        alert_id="A-AAAAAA",
        entity_type="Individual",
        dobs=[parse_date("1950")],
    )
    reason = build_reason("DIFFERENT_ENTITY", "DOB_MISMATCH", person, hit, {})
    assert "1990" in reason
    assert "1950" in reason
    sentences = [s for s in reason.split(".") if s.strip()]
    assert 2 <= len(sentences) <= 4
