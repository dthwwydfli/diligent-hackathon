"""[F] Minimal evidence + templated reasons (P9)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from namesake.dates import format_interval
from namesake.facts import HitFacts, Person


def build_reason(
    decision: str,
    reason_code: str,
    person: Optional[Person],
    hit: HitFacts,
    ctx: Dict[str, Any],
) -> str:
    parts: List[str] = []
    if reason_code == "DOB_MISMATCH" and person and person.dob:
        parts.append(
            f"The customer's date of birth {format_interval(person.dob)} "
            f"({person.verified_source or person.primary_id}) contradicts every birth date "
            f"the hit gives ({', '.join(format_interval(d) for d in hit.dobs) or 'none'})."
        )
    elif reason_code == "LOCATION_MISMATCH" and person:
        parts.append(
            f"Every country tied to the customer "
            f"({', '.join(sorted(person.countries)) or 'none'}) differs from every country "
            f"tied to the hit ({', '.join(sorted(hit.countries)) or 'none'})."
        )
    elif reason_code == "ENTITY_TYPE_MISMATCH":
        parts.append(
            f"The customer is a {person.entity_type if person else 'unknown'} and the hit is a "
            f"{hit.entity_type}."
        )
    elif reason_code == "DECEASED":
        parts.append("The hit's profile gives a date of death before the customer was screened.")
    elif reason_code == "TEMPORAL_IMPOSSIBILITY":
        parts.append(
            "The customer could not have done what the hit's profile reports at the earliest "
            "dated report (too young, or not yet incorporated)."
        )
    elif reason_code == "NAME_MISMATCH_VERIFIED" and person:
        parts.append(
            f"The customer's verified legal name ({person.verified_name}) does not agree with "
            f"any of the hit's names or aliases."
        )
    elif reason_code in {"NAME_DOB_LOCATION_MATCH", "NAME_DOB_MATCH"} and person and person.dob:
        parts.append(
            f"The customer's date of birth {format_interval(person.dob)} "
            f"({person.verified_source or person.primary_id}) agrees with the hit's "
            f"{' or '.join(format_interval(d) for d in hit.dobs) or 'date'}."
        )
        if reason_code == "NAME_DOB_LOCATION_MATCH":
            shared = sorted(person.countries & hit.countries)
            parts.append(
                f"Both the customer and the hit are linked to {', '.join(shared) or 'the same country'}."
            )
        parts.append("The customer's name agrees with the hit and nothing contradicts them.")
    elif reason_code == "NAME_LOCATION_MATCH" and person:
        shared = sorted(person.countries & hit.countries)
        parts.append(
            f"The company name agrees and both are linked to {', '.join(shared) or 'the same country'}."
        )
    elif reason_code == "AMBIGUOUS_CUSTOMER_RECORD":
        parts.append(
            "More than one person in the system of record fits the alert and they lead to "
            "different decisions."
        )
    else:
        parts.append("The evidence does not settle whether the hit is the customer.")

    if decision == "REVIEW" and reason_code == "INSUFFICIENT_DATA":
        # Counterfactual: name the single UNKNOWN that would decide it
        unknown = _first_unknown(ctx)
        if unknown:
            parts.append(f"If {unknown} were known with certainty, the decision could be settled.")
        else:
            parts.append("A human should review with the alert evidence.")

    # Keep 2–4 sentences
    text = " ".join(parts)
    sentences = [s.strip() for s in text.replace("?.", ".").split(".") if s.strip()]
    if len(sentences) > 4:
        sentences = sentences[:4]
    while len(sentences) < 2:
        sentences.append("A human should review with the alert evidence")
    return ". ".join(sentences) + "."


def _first_unknown(ctx: Dict[str, Any]) -> Optional[str]:
    checks = ctx.get("checks") or {}
    for key, cr in checks.items():
        if getattr(cr, "is_unknown", False):
            return key.replace("_", " ").lower()
    if ctx.get("name_ok") is None:
        return "the name comparison"
    if ctx.get("dob_ok") is None:
        return "the date of birth"
    return None
