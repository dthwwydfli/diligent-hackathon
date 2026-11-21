"""Wire resolve → hit facts → checks → table → explain into one decision."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from namesake.explain import build_reason
from namesake.facts import Person
from namesake.hitfacts import gather_hit_facts
from namesake.policy_table import aggregate_persons, decide_one_person
from namesake.resolve import resolve_customers
from namesake.schema import make_line
from namesake.store import DataStore


def decide(store: DataStore, hit_id: str) -> Dict[str, Any]:
    hit_row = store.hits[hit_id]
    alert = store.alert_for_hit(hit_id) or {}
    alert_id = hit_row.get("alert_id") or alert.get("alert_id") or "A-000000"
    hit = gather_hit_facts(store, hit_id)
    persons = resolve_customers(store, alert) if alert else []

    if not persons:
        # I11: screened details only
        screened = (alert or {}).get("customer") or {}
        ghost = Person(
            record_ids=[],
            entity_type=screened.get("entity_type") or "Individual",
            screened_name=screened.get("name"),
        )
        from namesake.countries import canonical_country
        from namesake.dates import parse_date

        ghost.dob = parse_date(screened.get("dob"))
        c = canonical_country(screened.get("country"))
        if c:
            ghost.countries.add(c)
        if screened.get("name"):
            from namesake.facts import CERTAIN, Fact

            ghost.names.append(Fact("name", screened["name"], "screened", "name", CERTAIN))
        decision, code, evidence, ctx = decide_one_person(ghost, hit, store)
        reason = build_reason(decision, code, ghost, hit, ctx)
        return make_line(hit_id, alert_id, decision, code, None, reason, evidence)

    results: List[Tuple[str, str, List[str], Dict[str, Any], Person]] = []
    for person in persons:
        d, c, ev, ctx = decide_one_person(person, hit, store)
        results.append((d, c, ev, ctx, person))

    decision, code, record_id, evidence, ctx = aggregate_persons(results)
    person = results[0][4] if len(results) == 1 else None
    if person is None and results:
        # multi-person: still explain from first for template fill
        person = results[0][4]
    reason = build_reason(decision, code, person, hit, ctx or results[0][3])
    return make_line(hit_id, alert_id, decision, code, record_id, reason, evidence)
