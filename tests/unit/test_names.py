"""Issue 3: P8 name comparison. Expected bools from the policy sentence."""

from __future__ import annotations

from namesake.names import (
    build_variant_map,
    can_use_name_for_clear_or_confirm,
    levenshtein,
    names_agree,
    tokenize_name,
)

VARIANTS = build_variant_map(
    [
        ["muhammad", "mohammed", "mohammad", "mohamed"],
        ["william", "will", "bill", "billy"],
    ]
)
FORMS = ["ltd", "gmbh", "sa", "ab", "as", "co", "na", "llc"]


def test_case_accents_punctuation_brackets() -> None:
    """P8: ignore case, accents, punctuation and anything in brackets."""
    assert names_agree("José María", "jose maria")
    assert names_agree("Ada (nickname) Lovelace", "Ada Lovelace")


def test_initials_not_parts() -> None:
    """P8: single letters are initials, not parts."""
    parts = tokenize_name("A. Ada Lovelace")
    assert "a" not in parts
    assert "ada" in parts and "lovelace" in parts


def test_variants() -> None:
    assert names_agree("Mohammed Ali", "Muhammad Ali", variants=VARIANTS)


def test_joined_split_i2() -> None:
    """P8/I2: Abdulsalam matches Abdul Salam as one part covering both."""
    assert names_agree("Abdulsalam Hassan", "Abdul Salam Hassan")


def test_edit_distance_budgets() -> None:
    """P8: ≤1 edit for 4–6 letters; ≤2 for 7+; under 4 must be identical."""
    # "jon" len 3 < 4 → must be identical → does not match "john"; only smith matches → no agree
    assert not names_agree("Jon Smith", "John Smith")
    # 4–6: 1 edit
    assert names_agree("Brian Cole", "Bryan Cole")
    # transposition = 2 edits (Levenshtein, not Damerau)
    assert levenshtein("ab", "ba") == 2
    # 7+ letters: budget 2
    assert names_agree("Catherine Pike", "Cathrine Pike")


def test_agree_two_parts_or_shorter_all() -> None:
    """P8: ≥2 parts match, or every part of the shorter name matches."""
    assert names_agree("Ada Lovelace Byron", "Ada Lovelace")
    assert names_agree("Li Wei", "Wei Li")


def test_placeholders_i12() -> None:
    parts = tokenize_name("NA TEST UNKNOWN")
    assert parts == []
    parts2 = tokenize_name("NULL NIL TBD DUMMY X XX 123")
    assert parts2 == []


def test_company_legal_forms_only_for_companies() -> None:
    """SPEC: legal forms stripped for companies only. 'as' kept on a person."""
    person = tokenize_name("As Bjorn", company_legal_forms=None)
    assert "as" in person
    company = tokenize_name("Nordic AS", company_legal_forms=FORMS)
    assert "as" not in company
    assert names_agree(
        "Nordic Fisheries Ltd",
        "Nordic Fisheries",
        company_legal_forms=FORMS,
        a_is_company=True,
        b_is_company=True,
    )


def test_under_two_parts_cannot_clear_or_confirm() -> None:
    """P8: individual with fewer than 2 real parts can be neither confirmed nor cleared on name."""
    assert not can_use_name_for_clear_or_confirm(tokenize_name("Madonna"))
    assert can_use_name_for_clear_or_confirm(tokenize_name("Ada Lovelace"))
