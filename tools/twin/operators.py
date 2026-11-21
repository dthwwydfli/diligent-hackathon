"""Mutation operators — one per policy branch (SPEC 7.1). Synthetic only."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class TwinCase:
    """Minimal person/hit world for one operator."""

    op: str
    expected_direction: str  # e.g. "to_DIFFERENT_ENTITY", "to_SAME_ENTITY", "to_REVIEW"
    customer_entity: str = "Individual"
    hit_entity: str = "Individual"
    customer_dob_year: Optional[int] = 1980
    hit_dob_years: List[int] = field(default_factory=lambda: [1980])
    customer_countries: Set[str] = field(default_factory=lambda: {"France"})
    hit_countries: Set[str] = field(default_factory=lambda: {"France"})
    name_agrees: bool = True
    verified_name_agrees: Optional[bool] = True
    countries_open: bool = False
    deceased_before_screen: Optional[bool] = False
    under_16: bool = False
    company_after_report: bool = False
    base_decision: Optional[str] = None
    note: str = ""


def all_operators() -> List[TwinCase]:
    """Hand-built mutants. Expected direction written from the policy branch first."""
    cases: List[TwinCase] = []

    # DOB clear vs agree
    cases.append(
        TwinCase(
            op="dob_outside_plus1",
            expected_direction="to_DIFFERENT_ENTITY",
            customer_dob_year=1990,
            hit_dob_years=[1950],
            note="P6 DOB: >1 year outside → clear",
        )
    )
    cases.append(
        TwinCase(
            op="dob_agree_year",
            expected_direction="to_SAME_ENTITY",
            customer_dob_year=1977,
            hit_dob_years=[1976, 1977],
            note="P7: year in hit set → agree",
        )
    )

    # Location
    cases.append(
        TwinCase(
            op="location_clear",
            expected_direction="to_DIFFERENT_ENTITY",
            customer_dob_year=None,
            hit_dob_years=[],
            customer_countries={"United States"},
            hit_countries={"Austria"},
            name_agrees=True,
            verified_name_agrees=None,
            note="P6 location: closed sets disjoint → clear",
        )
    )
    cases.append(
        TwinCase(
            op="location_open_blocks",
            expected_direction="to_REVIEW",
            customer_dob_year=None,
            hit_dob_years=[],
            customer_countries={"United States"},
            hit_countries={"Austria"},
            countries_open=True,
            verified_name_agrees=None,
            note="I9: open set → LOCATION UNKNOWN → no clear",
        )
    )

    # Type
    cases.append(
        TwinCase(
            op="person_vs_company",
            expected_direction="to_DIFFERENT_ENTITY",
            hit_entity="Company",
            note="P6 type",
        )
    )

    # Deceased
    cases.append(
        TwinCase(
            op="deceased_before",
            expected_direction="to_DIFFERENT_ENTITY",
            deceased_before_screen=True,
            note="P6 deceased",
        )
    )

    # Temporal
    cases.append(
        TwinCase(
            op="under_16",
            expected_direction="to_DIFFERENT_ENTITY",
            under_16=True,
            note="P6 temporal under-16",
        )
    )
    cases.append(
        TwinCase(
            op="company_after_report",
            expected_direction="to_DIFFERENT_ENTITY",
            customer_entity="Company",
            hit_entity="Company",
            company_after_report=True,
            name_agrees=True,
            note="P6 temporal company after report",
        )
    )

    # Name verified mismatch
    cases.append(
        TwinCase(
            op="name_mismatch_verified",
            expected_direction="to_DIFFERENT_ENTITY",
            verified_name_agrees=False,
            customer_dob_year=None,
            hit_dob_years=[],
            note="P6 name verified",
        )
    )

    return cases


def label_with_checker(case: TwinCase) -> Dict[str, Any]:
    from tools.checker.decide import decide_from_facts

    decision, code = decide_from_facts(
        customer_entity=case.customer_entity,
        hit_entity=case.hit_entity,
        customer_dob_year=case.customer_dob_year,
        hit_dob_years=list(case.hit_dob_years),
        customer_countries=set(case.customer_countries),
        hit_countries=set(case.hit_countries),
        name_agrees=case.name_agrees,
        verified_name_agrees=case.verified_name_agrees,
        countries_open=case.countries_open,
        deceased_before_screen=case.deceased_before_screen,
        under_16=case.under_16,
        company_after_report=case.company_after_report,
    )
    return {"decision": decision, "reason_code": code, "op": case.op}
