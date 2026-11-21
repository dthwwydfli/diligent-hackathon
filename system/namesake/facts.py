"""Facts with provenance and certainty (SPEC §5.3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Set

from namesake.dates import DateInterval

CERTAIN = "C"
UNCERTAIN = "U"


@dataclass
class Fact:
    kind: str
    value: Any
    source_id: str
    field: str = ""
    certainty: str = CERTAIN

    @property
    def is_certain(self) -> bool:
        return self.certainty == CERTAIN


@dataclass
class Person:
    """One resolved person (possibly merged records)."""

    record_ids: List[str]
    entity_type: str = "Individual"
    names: List[Fact] = field(default_factory=list)
    screened_name: Optional[str] = None
    dob: Optional[DateInterval] = None
    dob_facts: List[Fact] = field(default_factory=list)
    dob_unknown: bool = False
    countries: Set[str] = field(default_factory=set)
    country_facts: List[Fact] = field(default_factory=list)
    countries_open: bool = False  # I9
    verified_name: Optional[str] = None
    verified_dob: Optional[DateInterval] = None
    verified_doc_country: Optional[str] = None
    verified_source: Optional[str] = None
    has_approved_check: bool = False
    # Newer KYC note we could not read: do not use declared name or DOB.
    identity_unknown: bool = False
    evidence_ids: List[str] = field(default_factory=list)

    @property
    def primary_id(self) -> Optional[str]:
        return self.record_ids[0] if self.record_ids else None


@dataclass
class HitFacts:
    hit_id: str
    alert_id: str
    entity_type: str
    names: List[str] = field(default_factory=list)
    dobs: List[DateInterval] = field(default_factory=list)
    dob_unknown: bool = False  # unparsed birth cue blocks snippets (I1)
    countries: Set[str] = field(default_factory=set)
    countries_open: bool = False  # I9: an unmapped place-like value on the hit
    earliest_report: Optional[DateInterval] = None
    deceased_before_screen: Optional[bool] = None  # True/False/None(UNKNOWN)
    deceased_source: Optional[str] = None
    evidence_ids: List[str] = field(default_factory=list)
    incorporation: Optional[DateInterval] = None  # companies: dobs only


@dataclass
class CheckResult:
    name: str
    value: str  # TRUE / FALSE / UNKNOWN
    reason_code: Optional[str] = None
    evidence: List[str] = field(default_factory=list)
    facts: List[Fact] = field(default_factory=list)

    @property
    def is_true(self) -> bool:
        return self.value == "TRUE"

    @property
    def is_false(self) -> bool:
        return self.value == "FALSE"

    @property
    def is_unknown(self) -> bool:
        return self.value == "UNKNOWN"
