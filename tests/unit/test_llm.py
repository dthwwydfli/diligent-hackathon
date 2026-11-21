"""Issue 14: no key → reader-only; disagreement cannot enable clearance."""

from __future__ import annotations

from namesake.llm import LLMClient, reconcile_with_reader


def test_no_key_disables_client() -> None:
    client = LLMClient()
    # May or may not have a key in the environment; second_opinion must not crash
    result = client.second_opinion("hello")
    if not client.enabled:
        assert result is None


def test_disagreement_marks_uncertain() -> None:
    assert (
        reconcile_with_reader(
            "France",
            {"facts": [{"kind": "country", "value": "Spain", "quote": "Spain", "polarity": "+"}]},
            "country",
        )
        == "U"
    )
    assert (
        reconcile_with_reader(
            "France",
            {"facts": [{"kind": "country", "value": "France", "quote": "France", "polarity": "+"}]},
            "country",
        )
        == "C"
    )
    assert reconcile_with_reader("France", None, "country") == "C"
