"""[F] Reasons name this hit's own values. No filler sentence."""

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
    if decision == "REVIEW" and reason_code == "INSUFFICIENT_DATA":
        sentences = _review_sentences(person, hit, ctx)
    elif reason_code == "AMBIGUOUS_CUSTOMER_RECORD":
        sentences = [
            "More than one person in the system of record fits the alert.",
            "Those people lead to different decisions, so the customer record is ambiguous.",
        ]
    else:
        sentences = _decided_sentences(reason_code, person, hit)
    if len(sentences) > 4:
        sentences = sentences[:4]
    if len(sentences) < 2:
        sentences.append(_second_sentence(reason_code, person, hit))
    return ". ".join(sentences) + "."


def _decided_sentences(
    reason_code: str, person: Optional[Person], hit: HitFacts
) -> List[str]:
    hit_name = hit.names[0] if hit.names else "the listed name"
    if reason_code == "DOB_MISMATCH" and person and person.dob:
        source = person.verified_source or person.primary_id or "the customer record"
        return [
            (
                f"The customer's date of birth is {format_interval(person.dob)} ({source}) "
                f"but the hit's {_dob_origin(hit)} put its birth year at {_hit_years(hit)}"
            ),
            "Every birth date the hit gives is contradicted",
        ]
    if reason_code == "LOCATION_MISMATCH" and person:
        return [
            (
                f"The customer is linked only to {_country_list(person.countries)} "
                f"but the hit is linked only to {_country_list(hit.countries)}"
            ),
            "The customer's name and date of birth do not both agree with the hit, so the country difference clears it",
        ]
    if reason_code == "ENTITY_TYPE_MISMATCH":
        customer_type = person.entity_type if person else "unknown"
        return [
            f"The customer is a {customer_type} and the hit is a {hit.entity_type}",
            "A person and a company are not the same customer",
        ]
    if reason_code == "DECEASED":
        return [
            "The hit's profile gives a date of death before the customer was screened",
            "A person who died before screening cannot be this customer",
        ]
    if reason_code == "TEMPORAL_IMPOSSIBILITY":
        return [
            (
                "The customer could not have done what the hit's profile reports at the earliest "
                "dated report (too young, or not yet incorporated)"
            ),
            "That gap is a contradiction, so the hit is a different entity",
        ]
    if reason_code == "NAME_MISMATCH_VERIFIED" and person:
        source = person.verified_source or person.primary_id or "the approved check"
        return [
            (
                f"The customer's verified name is {person.verified_name} ({source}), "
                f"which does not match the hit's name {hit_name}"
            ),
            "No name or alias on the hit agrees with that verified name",
        ]
    if reason_code in {"NAME_DOB_LOCATION_MATCH", "NAME_DOB_MATCH"} and person and person.dob:
        source = person.verified_source or person.primary_id or "the customer record"
        sentences = [
            (
                f"The customer's date of birth {format_interval(person.dob)} ({source}) "
                f"agrees with the hit's {_hit_years(hit)}"
            )
        ]
        if reason_code == "NAME_DOB_LOCATION_MATCH":
            shared = sorted(person.countries & hit.countries)
            sentences.append(
                f"Both the customer and the hit are linked to {_country_list(shared)}"
            )
        sentences.append(f"The customer's name agrees with the hit's name {hit_name}")
        return sentences
    if reason_code == "NAME_LOCATION_MATCH" and person:
        shared = sorted(person.countries & hit.countries)
        return [
            f"Both the customer and the hit are linked to {_country_list(shared)}",
            f"The customer's name agrees with the hit's name {hit_name}",
        ]
    return [
        "The records for this hit do not settle whether it is the customer",
        "No certain contradiction and no full agreement were found",
    ]


def _review_sentences(
    person: Optional[Person], hit: HitFacts, ctx: Dict[str, Any]
) -> List[str]:
    """Say what agrees and what cannot be compared. No stock closer."""
    sentences: List[str] = []
    name_ok = ctx.get("name_ok")
    dob_ok = ctx.get("dob_ok")
    hit_name = hit.names[0] if hit.names else "the listed name"
    shared = sorted(person.countries & hit.countries) if person else []
    if name_ok is True and dob_ok is True and person and hit.countries and person.countries:
        if not shared:
            sentences.append(
                f"The customer is linked only to {_country_list(person.countries)} "
                f"but the hit is linked only to {_country_list(hit.countries)}"
            )
        sentences.append(f"The customer's name agrees with the hit's name {hit_name}")
        if person.dob:
            source = person.verified_source or person.primary_id or "the customer record"
            sentences.append(
                f"The customer's date of birth {format_interval(person.dob)} ({source}) "
                f"agrees with the hit's {_hit_years(hit)}, so the country difference does not clear the hit"
            )
        return sentences
    if shared:
        sentences.append(f"Both the customer and the hit are linked to {_country_list(shared)}")
    elif person and person.countries and hit.countries:
        sentences.append(
            f"The customer is linked only to {_country_list(person.countries)} "
            f"but the hit is linked only to {_country_list(hit.countries)}"
        )
    if name_ok is True:
        sentences.append(f"The customer's name agrees with the hit's name {hit_name}")
    elif name_ok is False and person and person.verified_name:
        sentences.append(
            f"The customer's verified name {person.verified_name} does not agree with the hit's name {hit_name}"
        )
    elif name_ok is None:
        sentences.append("The customer's name cannot be settled against the hit")
    if dob_ok is True and person and person.dob:
        source = person.verified_source or person.primary_id or "the customer record"
        sentences.append(
            f"The customer's date of birth {format_interval(person.dob)} ({source}) "
            f"agrees with the hit's {_hit_years(hit)}"
        )
    elif dob_ok is False and person and person.dob:
        sentences.append(
            f"The customer's date of birth {format_interval(person.dob)} "
            f"does not agree with the hit's {_hit_years(hit)}"
        )
    else:
        sentences.append(
            "Nothing in the customer's records contradicts the hit, and the date of birth "
            "cannot be compared with it, so the hit can be neither cleared nor confirmed"
        )
    return sentences


def _second_sentence(reason_code: str, person: Optional[Person], hit: HitFacts) -> str:
    if person and person.primary_id:
        return f"The customer record used here is {person.primary_id}"
    if hit.names:
        return f"The hit is listed as {hit.names[0]}"
    return f"The reason code on this hit is {reason_code}"


def _country_list(countries) -> str:
    names = sorted(c for c in countries if c)
    if not names:
        return "no country"
    return ", ".join(names)


def _hit_years(hit: HitFacts) -> str:
    seen = []
    for dob in hit.dobs:
        label = format_interval(dob)
        if label not in seen:
            seen.append(label)
    if not seen:
        return "no birth date"
    if len(seen) == 2:
        return f"{seen[0]} or {seen[1]}"
    return ", ".join(seen)


def _dob_origin(hit: HitFacts) -> str:
    sources = [dob.source or "" for dob in hit.dobs]
    if any(source.startswith("SR-") for source in sources):
        return "search results"
    if any(source == "profile" or source.startswith("profile") for source in sources):
        return "profile notes"
    return "listed dates"
