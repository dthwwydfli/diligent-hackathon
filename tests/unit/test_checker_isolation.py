"""Checker must not import the engine (SPEC test rule)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_IMPORT = re.compile(
    r"^\s*(?:from\s+(?:system\.)?namesake\b|import\s+(?:system\.)?namesake\b)",
    re.M,
)


def test_checker_does_not_import_engine() -> None:
    """tools/checker must not import system.namesake."""
    bad = []
    for path in (ROOT / "tools" / "checker").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if _IMPORT.search(text):
            bad.append(str(path))
    assert bad == []


def test_engine_does_not_import_tools() -> None:
    bad = []
    tool_import = re.compile(r"^\s*(?:from|import)\s+tools\b", re.M)
    for path in (ROOT / "system").rglob("*"):
        if path.suffix not in {".py", ""} and path.name != "run":
            continue
        if path.is_dir():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if tool_import.search(text):
            bad.append(str(path))
    assert bad == []


def test_checker_decide_matches_policy_table_cases() -> None:
    """Expected values written from POLICY P6/P7 before comparing implementations."""
    import sys

    sys.path.insert(0, str(ROOT))
    from tools.checker.decide import decide_from_facts

    assert decide_from_facts(
        customer_entity="Individual",
        hit_entity="Company",
        customer_dob_year=1980,
        hit_dob_years=[1980],
        customer_countries={"France"},
        hit_countries={"France"},
        name_agrees=True,
        verified_name_agrees=True,
        countries_open=False,
        deceased_before_screen=False,
        under_16=False,
        company_after_report=False,
    ) == ("DIFFERENT_ENTITY", "ENTITY_TYPE_MISMATCH")

    assert decide_from_facts(
        customer_entity="Individual",
        hit_entity="Individual",
        customer_dob_year=1990,
        hit_dob_years=[1950, 1951],
        customer_countries={"France"},
        hit_countries={"France"},
        name_agrees=True,
        verified_name_agrees=True,
        countries_open=False,
        deceased_before_screen=False,
        under_16=False,
        company_after_report=False,
    ) == ("DIFFERENT_ENTITY", "DOB_MISMATCH")

    assert decide_from_facts(
        customer_entity="Individual",
        hit_entity="Individual",
        customer_dob_year=None,
        hit_dob_years=[],
        customer_countries={"United States"},
        hit_countries={"Austria"},
        name_agrees=True,
        verified_name_agrees=None,
        countries_open=False,
        deceased_before_screen=False,
        under_16=False,
        company_after_report=False,
    ) == ("DIFFERENT_ENTITY", "LOCATION_MISMATCH")

    assert decide_from_facts(
        customer_entity="Individual",
        hit_entity="Individual",
        customer_dob_year=1977,
        hit_dob_years=[1976, 1977],
        customer_countries={"France"},
        hit_countries={"France"},
        name_agrees=True,
        verified_name_agrees=True,
        countries_open=False,
        deceased_before_screen=False,
        under_16=False,
        company_after_report=False,
    ) == ("SAME_ENTITY", "NAME_DOB_LOCATION_MATCH")
