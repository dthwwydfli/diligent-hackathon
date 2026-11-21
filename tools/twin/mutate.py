"""Labelled mutations of the dev folder. One copy, one system run.

Each case changes records for a single customer. The expected decision is fixed
by POLICY.md before the run. Hits of customers we did not touch must keep
their decision and reason code.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "system"))

from namesake.dates import parse_date, precise_day, precise_month  # noqa: E402
from namesake.hitfacts import (  # noqa: E402
    _snippet_age,
    accepted_snippet_years,
    hit_countries,
    listing_phrase,
)
from namesake.names import (  # noqa: E402
    build_variant_map,
    can_use_name_for_clear_or_confirm,
    tokenize_name,
)
from namesake.resolve import record_fits_screened, resolve_customers  # noqa: E402
from namesake.store import DataStore  # noqa: E402

DATA = os.path.join(ROOT, "data", "screening", "dev")
BASELINE = os.environ.get("TWIN_BASELINE", "/tmp/ns/r1.jsonl")
OUT_DIR = os.path.join(ROOT, "runs")
WORK = os.environ.get("TWIN_WORK", "/tmp/twin-data")
REPORT = os.path.join(OUT_DIR, "twin_report.json")
PER_OP = 24

MONTHS = [
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
POOL = ["Japan", "Brazil", "Nigeria", "Canada", "Egypt", "Chile"]
CITIES = {
    "Nigeria": "Lagos",
    "Pakistan": "Lahore",
    "India": "Pune",
    "Germany": "Leipzig",
    "France": "Lyon",
    "United States": "Dayton",
    "United Kingdom": "Leeds",
    "Brazil": "Recife",
    "Spain": "Bilbao",
    "Italy": "Bari",
}
SPELLINGS = {
    "United Kingdom": ["GB", "UK", "British", "United Kingdom"],
    "United States": ["US", "USA", "American", "United States"],
    "France": ["FR", "French", "France"],
    "Germany": ["DE", "German", "Germany"],
    "Nigeria": ["NG", "Nigerian", "Nigeria"],
    "Pakistan": ["PK", "Pakistani", "Pakistan"],
    "Brazil": ["BR", "Brazilian", "Brazil"],
    "Spain": ["ES", "Spanish", "Spain"],
    "Cote d'Ivoire": ["CI", "Ivory Coast", "Ivorian", "Cote d'Ivoire"],
}

JSONL = (
    "alerts.jsonl",
    "hits.jsonl",
    "customers.jsonl",
    "accounts.jsonl",
    "onboarding.jsonl",
    "kyc_checks.jsonl",
    "notes.jsonl",
    "search_results.jsonl",
)


@dataclass
class Case:
    op: str
    hit_id: str
    customer_key: Tuple[str, ...]
    expect: Dict[str, Any]
    forbid_de: bool = False
    base_decision: str = ""
    base_code: str = ""
    note: str = ""


@dataclass
class Bundle:
    """Mutable copies of the dev tables, indexed by id."""

    hits: Dict[str, Dict[str, Any]]
    customers: Dict[str, Dict[str, Any]]
    alerts: Dict[str, Dict[str, Any]]
    accounts: List[Dict[str, Any]]
    onboarding: List[Dict[str, Any]]
    checks: List[Dict[str, Any]]
    notes: List[Dict[str, Any]]
    search: List[Dict[str, Any]]
    extras: Dict[str, str] = field(default_factory=dict)
    _note: int = 0xF10000
    _cus: int = 970000
    _check: int = 0xF10000

    def new_note(self, email: str, channel: str, created: str, text: str) -> str:
        self._note += 1
        nid = f"NOTE-{self._note:06X}"
        self.notes.append(
            {
                "note_id": nid,
                "requester_email": email,
                "created_at": created,
                "channel": channel,
                "text": text,
            }
        )
        return nid

    def new_customer(self, template: Dict[str, Any], **over: Any) -> str:
        self._cus += 1
        cid = f"CUS-{self._cus:06d}"
        row = dict(template)
        row["record_id"] = cid
        row.update(over)
        self.customers[cid] = row
        return cid

    def new_check(self, applicant: str, **over: Any) -> str:
        self._check += 1
        cid = f"KYC-{self._check:06X}"
        row = {
            "check_id": cid,
            "applicant_id": applicant,
            "checked_at": "2024-01-01",
            "result": "approved",
            "document_type": "passport",
            "document_number": "",
            "document_country": "",
            "verified_name": "",
            "verified_dob": "",
            "provider": "twin",
        }
        row.update(over)
        self.checks.append(row)
        return cid


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_bundle(folder: str) -> Bundle:
    def rows(name: str) -> List[Dict[str, Any]]:
        return load_jsonl(os.path.join(folder, name))

    hits = {r["hit_id"]: r for r in rows("hits.jsonl")}
    customers = {r["record_id"]: r for r in rows("customers.jsonl")}
    alerts = {r["alert_id"]: r for r in rows("alerts.jsonl")}
    extras = {}
    for name in os.listdir(folder):
        if name not in JSONL and os.path.isfile(os.path.join(folder, name)):
            extras[name] = os.path.join(folder, name)
    return Bundle(
        hits=hits,
        customers=customers,
        alerts=alerts,
        accounts=rows("accounts.jsonl"),
        onboarding=rows("onboarding.jsonl"),
        checks=rows("kyc_checks.jsonl"),
        notes=rows("notes.jsonl"),
        search=rows("search_results.jsonl"),
        extras=extras,
    )


def save_bundle(bundle: Bundle, folder: str) -> None:
    os.makedirs(folder, exist_ok=True)
    tables = {
        "hits.jsonl": bundle.hits.values(),
        "customers.jsonl": bundle.customers.values(),
        "alerts.jsonl": bundle.alerts.values(),
        "accounts.jsonl": bundle.accounts,
        "onboarding.jsonl": bundle.onboarding,
        "kyc_checks.jsonl": bundle.checks,
        "notes.jsonl": bundle.notes,
        "search_results.jsonl": bundle.search,
    }
    for name, items in tables.items():
        with open(os.path.join(folder, name), "w", encoding="utf-8") as handle:
            for row in items:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    for name, src in bundle.extras.items():
        shutil.copy(src, os.path.join(folder, name))


def dob_text(iv) -> str:
    if precise_day(iv) is not None:
        return f"{iv.y_lo:04d}-{iv.m_lo:02d}-{iv.d_lo:02d}"
    if precise_month(iv) is not None:
        return f"{iv.y_lo:04d}-{iv.m_lo:02d}"
    return str(iv.y_lo)


def usable_name(person) -> Optional[str]:
    cands: List[str] = []
    if person.verified_name:
        cands.append(person.verified_name)
    cands.extend(fact.value for fact in person.names if fact.kind == "name")
    if person.screened_name:
        cands.append(person.screened_name)
    for name in cands:
        if can_use_name_for_clear_or_confirm(tokenize_name(name)):
            return name
    return None


def foreign(have: Set[str]) -> str:
    for country in POOL:
        if country not in have:
            return country
    return "Japan"


def clear_hit_birth(hit: Dict[str, Any]) -> None:
    """Drop every birth cue except the dobs field we set ourselves."""
    hit["profile_notes"] = ""
    hit["deceased_date"] = None


def set_hit_countries(hit: Dict[str, Any], countries: Sequence[str]) -> None:
    hit["countries"] = list(countries)
    hit["nationality"] = []
    hit["citizenship"] = []
    hit["addresses"] = []
    hit["place_of_birth"] = None


def set_hit_name(hit: Dict[str, Any], name: str) -> None:
    hit["name"] = name
    hit["best_matching_name"] = name
    hit["aliases"] = []
    hit["first_name"] = None
    hit["middle_name"] = None
    hit["last_name"] = None


def paint_screened(
    bundle: Bundle,
    hid: str,
    *,
    name: Optional[str] = None,
    dob: Optional[str] = None,
    country: Optional[str] = None,
    entity: Optional[str] = None,
) -> None:
    """Unlinked alerts only find a customer who still matches the screened details."""
    alert = bundle.alerts[bundle.hits[hid]["alert_id"]]
    screened = dict(alert.get("customer") or {})
    if name is not None:
        screened["name"] = name
    if dob is not None:
        screened["dob"] = dob
    if country is not None:
        screened["country"] = country
    if entity is not None:
        screened["entity_type"] = entity
    alert["customer"] = screened


def linked(store: DataStore, hid: str) -> bool:
    alert = store.alert_for_hit(hid) or {}
    return bool(alert.get("account_ref") or alert.get("login_handle") or alert.get("email"))


def customer_email(bundle: Bundle, person) -> Optional[str]:
    for rid in person.record_ids:
        email = (bundle.customers[rid].get("email") or "").strip()
        if email:
            return email
    return None


def rewrite_verified_dob(bundle: Bundle, person, dob: str, name: Optional[str] = None) -> None:
    """Put this DOB on the record and on the approved check the engine will read."""
    for rid in person.record_ids:
        bundle.customers[rid]["dob"] = dob
    source = person.verified_source or ""
    if source.startswith("KYC-"):
        for check in bundle.checks:
            if check.get("check_id") == source:
                check["verified_dob"] = dob
                if name:
                    check["verified_name"] = name
                return
    if source.startswith("NOTE-"):
        for note in bundle.notes:
            if note.get("note_id") == source:
                who = name or person.verified_name or "ANA LIMA"
                country = person.verified_doc_country or "France"
                note["text"] = (
                    f"Successful ID verification. {who.upper()}. "
                    f"Born {MONTHS[int(dob[5:7])]} {dob[:4]}, day {int(dob[8:10])}. "
                    f"Document country {country}."
                )
                note["channel"] = "kyc"
                return


def main() -> int:
    baseline = {j["hit_id"]: j for j in load_jsonl(BASELINE)}
    store = DataStore(DATA)
    print("resolving customers", flush=True)
    people = {}
    keys = {}
    for hid in store.hit_ids_sorted():
        alert = store.alert_for_hit(hid) or {}
        persons = resolve_customers(store, alert) if alert else []
        people[hid] = persons
        if persons:
            ids = tuple(sorted({rid for person in persons for rid in person.record_ids}))
        else:
            ids = ("alert", alert.get("alert_id") or hid)
        keys[hid] = ids

    bundle = load_bundle(DATA)
    used: Set[Tuple[str, ...]] = set()
    cases: List[Case] = []

    def take(hid: str) -> bool:
        key = keys[hid]
        if key in used:
            return False
        if hid not in baseline:
            return False
        used.add(key)
        return True

    def add(case: Case) -> None:
        cases.append(case)

    def base_of(hid: str) -> Tuple[str, str]:
        row = baseline[hid]
        return row["decision"], row["reason_code"]

    def add_search(query: str, snippet: str) -> None:
        bundle.search.append(
            {
                "result_id": f"SR-TWIN{len(bundle.search):05d}",
                "query": query,
                "snippet": snippet,
                "source": "twin",
                "title": "twin",
            }
        )

    def prepare_controlled(hid: str, person, name: str) -> None:
        hit = bundle.hits[hid]
        clear_hit_birth(hit)
        hit["entity_type"] = "Individual"
        hit["dobs"] = []
        set_hit_name(hit, name)
        set_hit_countries(hit, ["France"])
        rewrite_verified_dob(bundle, person, "1960-05-05", name=name)
        for rid in person.record_ids:
            rec = bundle.customers[rid]
            rec["entity_type"] = "Individual"
            rec["full_name"] = name
            rec["preferred_name"] = name
            rec["residence_country"] = "France"
            rec["nationality"] = "France"
        source = person.verified_source or ""
        if source.startswith("KYC-"):
            for check in bundle.checks:
                if check.get("check_id") == source:
                    check["document_country"] = "France"
                    check["result"] = "approved"
        paint_screened(bundle, hid, name=name, dob="1960-05-05", country="France", entity="Individual")

    # T13 before other operators, so the merge cases are not starved
    n = 0
    for hid in store.hit_ids_sorted():
        if n >= PER_OP:
            break
        persons = people[hid]
        if len(persons) != 1:
            continue
        person = persons[0]
        if person.identity_unknown or not person.verified_name or not person.verified_source:
            continue
        if not can_use_name_for_clear_or_confirm(tokenize_name(person.verified_name)):
            continue
        anchor = None
        for rid in person.record_ids:
            rec = bundle.customers.get(rid) or {}
            phone = "".join(ch for ch in str(rec.get("phone") or "") if ch.isdigit())
            iv = parse_date(rec.get("dob"))
            if phone and iv is not None and precise_day(iv) is not None:
                anchor = rec
                break
        if anchor is None or not take(hid):
            continue
        name = person.verified_name
        hit = bundle.hits[hid]
        clear_hit_birth(hit)
        hit["entity_type"] = "Individual"
        hit["dobs"] = ["1970-01-01"]
        set_hit_name(hit, name)
        set_hit_countries(hit, ["Japan"])
        alert = store.alert_for_hit(hid) or {}
        city = (alert.get("customer") or {}).get("city")
        for rid in person.record_ids:
            rec = bundle.customers[rid]
            rec["full_name"] = name
            rec["preferred_name"] = name
            rec["dob"] = "1960-05-05"
            rec["residence_country"] = "France"
            rec["nationality"] = "France"
            rec["entity_type"] = "Individual"
            if city:
                rec["city"] = city
                rec["address"] = city
        source = person.verified_source or ""
        if source.startswith("KYC-"):
            for check in bundle.checks:
                if check.get("check_id") == source:
                    check["verified_name"] = name
                    check["verified_dob"] = ""
                    check["document_country"] = "France"
        elif source.startswith("NOTE-"):
            for note in bundle.notes:
                if note.get("note_id") == source:
                    note["channel"] = "kyc"
                    note["text"] = (
                        f"Successful ID verification. Holder: {name.upper()}. "
                        "Document country France."
                    )
        paint_screened(bundle, hid, name=name, dob="1960-05-05", country="France", entity="Individual")
        doc = f"TWINDOC{n:05d}"
        app_b = f"APP-B{n:05d}"
        app_c = f"APP-C{n:05d}"
        bid = bundle.new_customer(
            anchor,
            full_name="Other Holder",
            dob="1960-05-05",
            phone=anchor.get("phone"),
            email=f"twin-merge-b-{n}@example.test",
            residence_country="France",
            nationality="France",
        )
        cid = bundle.new_customer(
            anchor,
            full_name="Other Holder",
            dob="1975-06-06",
            phone=f"555029{n:04d}",
            email=f"twin-merge-c-{n}@example.test",
            residence_country="Japan",
            nationality="Japan",
        )
        bundle.onboarding.append(
            {"account_id": "TWIN-ACC", "customer_id": bid, "kyc_applicant_id": app_b, "onboarded_at": "2020-01-01"}
        )
        bundle.onboarding.append(
            {"account_id": "TWIN-ACC", "customer_id": cid, "kyc_applicant_id": app_c, "onboarded_at": "2020-01-01"}
        )
        bundle.new_check(
            app_b, checked_at="1990-01-01", document_number=doc, verified_name="", verified_dob=""
        )
        bundle.new_check(
            app_c, checked_at="1990-01-01", document_number=doc, verified_name="", verified_dob=""
        )
        decision, code = base_of(hid)
        add(
            Case(
                "T13",
                hid,
                keys[hid],
                {"decision": "REVIEW"},
                forbid_de=True,
                base_decision=decision,
                base_code=code,
                note="phone merge plus document chain",
            )
        )
        n += 1

    # Manufactured snippet wordings. The birth year is known from the age and the date.
    for op, keep_phrase, prefix in (("T17", True, "Brant"), ("T18", False, "Cress")):
        n = 0
        for hid in store.hit_ids_sorted():
            if n >= PER_OP:
                break
            persons = people[hid]
            if len(persons) != 1:
                continue
            person = persons[0]
            if person.identity_unknown or not person.verified_source:
                continue
            if (person.entity_type or "").lower() == "company":
                continue
            if not take(hid):
                continue
            name = f"{prefix}{chr(65 + n)} Quinn"
            prepare_controlled(hid, person, name)
            phrase = listing_phrase(store.hits[hid])
            query = " ".join(sorted(tokenize_name(name)))
            if keep_phrase:
                snippet = f"In March 2018, {name}, 52, was {phrase} in France."
                expect = {"decision": "DIFFERENT_ENTITY", "code": "DOB_MISMATCH"}
                forbid = False
            else:
                snippet = f"In March 2018, {name}, 52, was mentioned in a filing in France."
                expect = {"decision": "REVIEW"}
                forbid = True
            add_search(query, snippet)
            decision, code = base_of(hid)
            add(
                Case(
                    op,
                    hid,
                    keys[hid],
                    expect,
                    forbid_de=forbid,
                    base_decision=decision,
                    base_code=code,
                )
            )
            n += 1

    # T1 location exception
    n = 0
    for hid in store.hit_ids_sorted():
        if n >= PER_OP:
            break
        row = baseline.get(hid)
        if not row or row["reason_code"] != "LOCATION_MISMATCH":
            continue
        persons = people[hid]
        if len(persons) != 1 or persons[0].identity_unknown or persons[0].dob is None:
            continue
        person = persons[0]
        if (person.entity_type or "").lower() == "company":
            continue
        if (store.hits[hid].get("entity_type") or "").lower() == "company":
            continue
        name = usable_name(person)
        if not name or not take(hid):
            continue
        hit = bundle.hits[hid]
        clear_hit_birth(hit)
        hit["entity_type"] = "Individual"
        hit["dobs"] = [dob_text(person.dob)]
        set_hit_name(hit, name)
        set_hit_countries(hit, [foreign(person.countries)])
        decision, code = base_of(hid)
        add(
            Case(
                "T1",
                hid,
                keys[hid],
                {"decision": "REVIEW"},
                forbid_de=True,
                base_decision=decision,
                base_code=code,
                note="name and DOB agree, countries differ",
            )
        )
        n += 1

    # T2 DOB two or more years out
    n = 0
    for hid in store.hit_ids_sorted():
        if n >= PER_OP:
            break
        persons = people[hid]
        if len(persons) != 1 or persons[0].dob is None or not persons[0].dob.certain:
            continue
        person = persons[0]
        if person.identity_unknown or (person.entity_type or "").lower() == "company":
            continue
        if (store.hits[hid].get("entity_type") or "").lower() == "company":
            continue
        if not take(hid):
            continue
        year = person.dob.y_lo - 5
        hit = bundle.hits[hid]
        clear_hit_birth(hit)
        hit["entity_type"] = "Individual"
        hit["dobs"] = [str(year)]
        decision, code = base_of(hid)
        add(
            Case(
                "T2",
                hid,
                keys[hid],
                {"decision": "DIFFERENT_ENTITY", "code": "DOB_MISMATCH"},
                base_decision=decision,
                base_code=code,
            )
        )
        n += 1

    # T3 same year, different month
    n = 0
    for hid in store.hit_ids_sorted():
        if n >= PER_OP:
            break
        persons = people[hid]
        if len(persons) != 1 or persons[0].dob is None or not persons[0].dob.certain:
            continue
        person = persons[0]
        if precise_month(person.dob) is None or person.identity_unknown:
            continue
        if (person.entity_type or "").lower() == "company":
            continue
        if (store.hits[hid].get("entity_type") or "").lower() == "company":
            continue
        if not take(hid):
            continue
        month = person.dob.m_lo % 12 + 1
        hit = bundle.hits[hid]
        clear_hit_birth(hit)
        hit["entity_type"] = "Individual"
        hit["dobs"] = [f"{person.dob.y_lo:04d}-{month:02d}"]
        decision, code = base_of(hid)
        add(
            Case(
                "T3",
                hid,
                keys[hid],
                {"decision": "DIFFERENT_ENTITY", "code": "DOB_MISMATCH"},
                base_decision=decision,
                base_code=code,
            )
        )
        n += 1

    # T4 within one year: must not be DOB_MISMATCH
    n = 0
    for hid in store.hit_ids_sorted():
        if n >= PER_OP:
            break
        persons = people[hid]
        if len(persons) != 1 or persons[0].dob is None or not persons[0].dob.certain:
            continue
        person = persons[0]
        if person.identity_unknown or (person.entity_type or "").lower() == "company":
            continue
        if (store.hits[hid].get("entity_type") or "").lower() == "company":
            continue
        if not take(hid):
            continue
        hit = bundle.hits[hid]
        clear_hit_birth(hit)
        hit["entity_type"] = "Individual"
        hit["dobs"] = [str(person.dob.y_lo + 1)]
        decision, code = base_of(hid)
        add(
            Case(
                "T4",
                hid,
                keys[hid],
                {"not_code": "DOB_MISMATCH"},
                base_decision=decision,
                base_code=code,
            )
        )
        n += 1

    # T6 first so location customers are not all spent on T1 and T5
    n = 0
    for hid in store.hit_ids_sorted():
        if n >= PER_OP:
            break
        row = baseline.get(hid)
        if not row or row["reason_code"] != "LOCATION_MISMATCH":
            continue
        persons = people[hid]
        if len(persons) != 1:
            continue
        person = persons[0]
        email = customer_email(bundle, person)
        city = "Lagos"
        for country in list(person.countries) + list(store.hits[hid].get("countries") or []):
            plain = str(country).split("[")[0].strip()
            if plain in CITIES:
                city = CITIES[plain]
                break
        if not email or not take(hid):
            continue
        bundle.new_note(
            email,
            "support",
            "2024-06-02",
            f"The client lived in {city} from 2010 to 2015 before the current address.",
        )
        decision, code = base_of(hid)
        add(
            Case(
                "T6",
                hid,
                keys[hid],
                {"not_code": "LOCATION_MISMATCH"},
                base_decision=decision,
                base_code=code,
            )
        )
        n += 1

    # T5 reworded residence in a hit country
    n = 0
    for hid in store.hit_ids_sorted():
        if n >= PER_OP:
            break
        row = baseline.get(hid)
        if not row or row["reason_code"] != "LOCATION_MISMATCH":
            continue
        persons = people[hid]
        if len(persons) != 1:
            continue
        person = persons[0]
        email = customer_email(bundle, person)
        listed = list(store.hits[hid].get("countries") or [])
        country = None
        for raw in listed:
            text = str(raw).split("[")[0].strip()
            if text and text.lower() not in {"international", "europe"}:
                country = text
                break
        if not email or not country or not take(hid):
            continue
        bundle.new_note(
            email,
            "support",
            "2024-06-01",
            f"Before moving here the client spent six years in {country}. Previous address was there from 2010 to 2016.",
        )
        decision, code = base_of(hid)
        add(
            Case(
                "T5",
                hid,
                keys[hid],
                {"not_code": "LOCATION_MISMATCH"},
                base_decision=decision,
                base_code=code,
            )
        )
        n += 1

    # T7 newer rejected note does not change the decision
    n = 0
    for hid in store.hit_ids_sorted():
        if n >= PER_OP:
            break
        persons = people[hid]
        if len(persons) != 1 or not persons[0].has_approved_check:
            continue
        email = customer_email(bundle, persons[0])
        if not email or not take(hid):
            continue
        bundle.new_note(
            email,
            "kyc",
            "2026-11-20",
            "Identity check failed and was rejected. The document was expired. "
            "Holder on the failed check: SOMEONE ELSE. DOB 1900-01-01.",
        )
        decision, code = base_of(hid)
        add(
            Case(
                "T7",
                hid,
                keys[hid],
                {"unchanged": True},
                forbid_de=decision != "DIFFERENT_ENTITY",
                base_decision=decision,
                base_code=code,
            )
        )
        n += 1

    # T8 approved facts restated in a new wording
    n = 0
    for hid in store.hit_ids_sorted():
        if n >= PER_OP:
            break
        persons = people[hid]
        if len(persons) != 1:
            continue
        person = persons[0]
        if (
            person.identity_unknown
            or not person.verified_name
            or person.verified_dob is None
            or not person.verified_dob.certain
            or precise_day(person.verified_dob) is None
            or not person.verified_doc_country
        ):
            continue
        if not can_use_name_for_clear_or_confirm(tokenize_name(person.verified_name)):
            continue
        email = customer_email(bundle, person)
        if not email or not take(hid):
            continue
        dob = person.verified_dob
        bundle.new_note(
            email,
            "kyc",
            "2026-11-19",
            f"ID check OK (Persona). Holder: {person.verified_name.upper()}. "
            f"D.O.B. {dob.d_lo} {MONTHS[dob.m_lo]} {dob.y_lo}. "
            f"Doc: {person.verified_doc_country} passport.",
        )
        decision, code = base_of(hid)
        add(
            Case(
                "T8",
                hid,
                keys[hid],
                {"unchanged": True},
                forbid_de=decision != "DIFFERENT_ENTITY",
                base_decision=decision,
                base_code=code,
            )
        )
        n += 1

    # T9 death before screening, and a date after that must not change the hit
    n_before = n_after = 0
    for hid in store.hit_ids_sorted():
        if n_before >= PER_OP // 2 and n_after >= PER_OP // 2:
            break
        persons = people[hid]
        if len(persons) != 1:
            continue
        person = persons[0]
        hit_row = store.hits[hid]
        if (person.entity_type or "").lower() == "company":
            continue
        if (hit_row.get("entity_type") or "").lower() == "company":
            continue
        alert = store.alert_for_hit(hid) or {}
        if not alert.get("screened_at") or not take(hid):
            continue
        hit = bundle.hits[hid]
        decision, code = base_of(hid)
        if n_before < PER_OP // 2:
            hit["deceased_date"] = "1990-01-01"
            add(
                Case(
                    "T9",
                    hid,
                    keys[hid],
                    {"decision": "DIFFERENT_ENTITY", "code": "DECEASED"},
                    base_decision=decision,
                    base_code=code,
                    note="death before screening",
                )
            )
            n_before += 1
        else:
            hit["deceased_date"] = "2099-01-01"
            add(
                Case(
                    "T9",
                    hid,
                    keys[hid],
                    {"unchanged": True},
                    forbid_de=decision != "DIFFERENT_ENTITY",
                    base_decision=decision,
                    base_code=code,
                    note="death after screening",
                )
            )
            n_after += 1

    # T10 under 16, and a company incorporated after the report
    n_age = n_co = 0
    for hid in store.hit_ids_sorted():
        if n_age >= 16 and n_co >= 8:
            break
        persons = people[hid]
        if len(persons) != 1 or persons[0].identity_unknown:
            continue
        person = persons[0]
        if not take(hid):
            continue
        hit = bundle.hits[hid]
        decision, code = base_of(hid)
        if n_age < 16 and (person.entity_type or "").lower() != "company":
            if (hit.get("entity_type") or "").lower() == "company":
                used.discard(keys[hid])
                continue
            hit["deceased_date"] = None
            hit["entity_type"] = "Individual"
            hit["profile_notes"] = (
                "According to Registry notice; January 15, 2010: the subject was listed."
            )
            hit["dobs"] = []
            rewrite_verified_dob(bundle, person, "2008-01-01")
            paint_screened(bundle, hid, dob="2008-01-01")
            add(
                Case(
                    "T10",
                    hid,
                    keys[hid],
                    {"decision": "DIFFERENT_ENTITY", "code": "TEMPORAL_IMPOSSIBILITY"},
                    base_decision=decision,
                    base_code=code,
                    note="under 16",
                )
            )
            n_age += 1
        elif n_co < 8:
            hit["deceased_date"] = None
            hit["entity_type"] = "Company"
            hit["dobs"] = ["2020-01-01"]
            hit["profile_notes"] = (
                "According to Registry notice; January 15, 2010: the company was listed."
            )
            for rid in person.record_ids:
                bundle.customers[rid]["entity_type"] = "Company"
            add(
                Case(
                    "T10",
                    hid,
                    keys[hid],
                    {"decision": "DIFFERENT_ENTITY", "code": "TEMPORAL_IMPOSSIBILITY"},
                    base_decision=decision,
                    base_code=code,
                    note="incorporated after the report",
                )
            )
            n_co += 1

    # T11 person versus company
    n = 0
    for hid in store.hit_ids_sorted():
        if n >= PER_OP:
            break
        persons = people[hid]
        if len(persons) != 1:
            continue
        person = persons[0]
        hit_type = (store.hits[hid].get("entity_type") or "Individual").lower()
        cust_type = (person.entity_type or "Individual").lower()
        if hit_type == "company" and cust_type == "company":
            continue
        if hit_type != "company" and cust_type == "company":
            continue
        if not take(hid):
            continue
        hit = bundle.hits[hid]
        if cust_type == "company":
            hit["entity_type"] = "Individual"
        else:
            hit["entity_type"] = "Company"
        decision, code = base_of(hid)
        add(
            Case(
                "T11",
                hid,
                keys[hid],
                {"decision": "DIFFERENT_ENTITY", "code": "ENTITY_TYPE_MISMATCH"},
                base_decision=decision,
                base_code=code,
            )
        )
        n += 1

    # T14 placeholder name
    n = 0
    for hid in store.hit_ids_sorted():
        if n >= PER_OP:
            break
        persons = people[hid]
        if len(persons) != 1 or (persons[0].entity_type or "").lower() == "company":
            continue
        if not linked(store, hid) or not take(hid):
            continue
        person = persons[0]
        label = "Ana N/A" if n % 2 == 0 else "TEST"
        for rid in person.record_ids:
            rec = bundle.customers[rid]
            rec["full_name"] = label
            rec["preferred_name"] = label
            rec["login_name"] = label
        source = person.verified_source or ""
        if source.startswith("KYC-"):
            for check in bundle.checks:
                if check.get("check_id") == source:
                    check["verified_name"] = label
        if source.startswith("NOTE-"):
            for note in bundle.notes:
                if note.get("note_id") == source:
                    note["text"] = (
                        f"Successful ID verification. Holder: {label}. "
                        "Born January 1980, day 2. Document country France."
                    )
        decision, code = base_of(hid)
        add(
            Case(
                "T14",
                hid,
                keys[hid],
                {
                    "not_codes": [
                        "NAME_MISMATCH_VERIFIED",
                        "NAME_DOB_MATCH",
                        "NAME_DOB_LOCATION_MATCH",
                        "NAME_LOCATION_MATCH",
                    ]
                },
                base_decision=decision,
                base_code=code,
            )
        )
        n += 1

    # T15 hyphen and edit-distance boundaries, names overwritten on both sides
    agree_pairs = [
        ("Brian Cole", "Bryan Cole", True),
        ("Markus Muller", "Markus A. Muller-Kagi", True),
        ("Abdulsalam Hassan", "Abdul Salam Hassan", True),
        ("Catherine Pike", "Cathrine Pike", True),
    ]
    disagree_pairs = [
        ("Pat Smith", "Pate Smith", False),
        ("Ann Cole", "Anne Cole", False),
    ]
    n = 0
    pair_i = 0
    pool = agree_pairs + disagree_pairs
    for hid in store.hit_ids_sorted():
        if n >= PER_OP:
            break
        persons = people[hid]
        if len(persons) != 1 or not persons[0].has_approved_check:
            continue
        person = persons[0]
        if person.identity_unknown or (person.entity_type or "").lower() == "company":
            continue
        if not person.verified_source or not take(hid):
            continue
        left, right, should_agree = pool[pair_i % len(pool)]
        pair_i += 1
        hit = bundle.hits[hid]
        clear_hit_birth(hit)
        hit["entity_type"] = "Individual"
        hit["dobs"] = ["1980-05-05"]
        set_hit_name(hit, right)
        set_hit_countries(hit, ["France"])
        for rid in person.record_ids:
            rec = bundle.customers[rid]
            rec["entity_type"] = "Individual"
            rec["dob"] = "1980-05-05"
            rec["full_name"] = left
            rec["preferred_name"] = left
            rec["residence_country"] = "France"
            rec["nationality"] = "France"
        source = person.verified_source
        if source.startswith("KYC-"):
            for check in bundle.checks:
                if check.get("check_id") == source:
                    check["verified_name"] = left
                    check["verified_dob"] = "1980-05-05"
                    check["document_country"] = "France"
                    check["result"] = "approved"
        elif source.startswith("NOTE-"):
            for note in bundle.notes:
                if note.get("note_id") == source:
                    note["channel"] = "kyc"
                    note["text"] = (
                        f"Successful ID verification. Holder: {left.upper()}. "
                        "Born May 1980, day 5. Document country France."
                    )
        paint_screened(bundle, hid, name=left, dob="1980-05-05", country="France")
        decision, code = base_of(hid)
        if should_agree:
            expect = {"decision": "SAME_ENTITY"}
            forbid = True
        else:
            expect = {"decision": "DIFFERENT_ENTITY", "code": "NAME_MISMATCH_VERIFIED"}
            forbid = False
        add(
            Case(
                "T15",
                hid,
                keys[hid],
                expect,
                forbid_de=forbid,
                base_decision=decision,
                base_code=code,
                note=f"{left} vs {right}",
            )
        )
        n += 1

    # T16 country spelling
    n = 0
    for hid in store.hit_ids_sorted():
        if n >= PER_OP:
            break
        persons = people[hid]
        if len(persons) != 1:
            continue
        person = persons[0]
        country = next((c for c in person.countries if c in SPELLINGS), None)
        if country is None or not take(hid):
            continue
        aliases = SPELLINGS[country]
        spelling = aliases[n % len(aliases)]
        for rid in person.record_ids:
            rec = bundle.customers[rid]
            for field in ("residence_country", "nationality"):
                if _same_country(rec.get(field), country):
                    rec[field] = spelling
        hit = bundle.hits[hid]
        if hit.get("countries"):
            hit["countries"] = [spelling if _same_country(item, country) else item for item in hit["countries"]]
        decision, code = base_of(hid)
        add(
            Case(
                "T16",
                hid,
                keys[hid],
                {"unchanged": True},
                forbid_de=decision != "DIFFERENT_ENTITY",
                base_decision=decision,
                base_code=code,
                note=f"{country} written as {spelling}",
            )
        )
        n += 1

    variants = build_variant_map(store.name_variants.get("groups") or [])
    forms = list(store.name_variants.get("company_legal_forms") or [])

    # T12 joint account: a second holder who also fits, opposite entity type
    n = 0
    for hid in store.hit_ids_sorted():
        if n >= PER_OP:
            break
        persons = people[hid]
        if len(persons) != 1:
            continue
        alert = store.alert_for_hit(hid) or {}
        account = alert.get("account_ref")
        holders = store.account_holders.get(account or "", [])
        if not account or len(holders) != 1:
            continue
        person = persons[0]
        screened = alert.get("customer") or {}
        if not any(
            record_fits_screened(store.customers[rid], screened, variants, forms)
            for rid in person.record_ids
            if rid in store.customers
        ):
            continue
        template = bundle.customers.get(person.record_ids[0])
        if template is None or not take(hid):
            continue
        hit = store.hits[hid]
        other = "Company" if (hit.get("entity_type") or "").lower() != "company" else "Individual"
        city = screened.get("city") or template.get("city") or ""
        draft = dict(template)
        draft.update(
            {
                "full_name": screened.get("name") or template.get("full_name"),
                "preferred_name": screened.get("name") or template.get("preferred_name"),
                "dob": screened.get("dob") or template.get("dob"),
                "residence_country": screened.get("country") or template.get("residence_country"),
                "city": city,
                "address": city or template.get("address"),
                "entity_type": other,
                "phone": f"555019{n:04d}",
                "email": f"twin-joint-{n}@example.test",
            }
        )
        if not record_fits_screened(draft, screened, variants, forms):
            used.discard(keys[hid])
            continue
        cid = bundle.new_customer(template, **{k: draft[k] for k in draft if k != "record_id"})
        bundle.accounts.append(
            {
                "account_id": account,
                "customer_id": cid,
                "login_handle": f"twinjoint{n}",
                "opened_at": "2020-01-01",
                "phone": draft["phone"],
                "status": "open",
            }
        )
        decision, code = base_of(hid)
        if decision == "DIFFERENT_ENTITY":
            expect = {"decision": "DIFFERENT_ENTITY", "record": "AMBIGUOUS"}
            forbid = False
        else:
            expect = {
                "decision": "REVIEW",
                "code": "AMBIGUOUS_CUSTOMER_RECORD",
                "record": "AMBIGUOUS",
            }
            forbid = True
        add(
            Case(
                "T12",
                hid,
                keys[hid],
                expect,
                forbid_de=forbid,
                base_decision=decision,
                base_code=code,
            )
        )
        n += 1

    def snippet_rows(hid: str) -> List[Dict[str, Any]]:
        hit = store.hits[hid]
        countries = hit_countries(hit)
        accepted = {
            iv.source
            for iv in accepted_snippet_years(store, hit, countries)
            if str(iv.source).startswith("SR-")
        }
        if not accepted:
            return []
        return [row for row in bundle.search if row.get("result_id") in accepted]

    # T17 snippet age, new wording, same birth years
    n = 0
    for hid in store.hit_ids_sorted():
        if n >= PER_OP:
            break
        rows = snippet_rows(hid)
        if not rows or not take(hid):
            continue
        hit = bundle.hits[hid]
        phrase = listing_phrase(store.hits[hid])
        country = next(iter(hit_countries(store.hits[hid])), None)
        if not country:
            used.discard(keys[hid])
            continue
        ok = True
        for srow in rows:
            age = _snippet_age(srow.get("snippet") or "")
            year = _snippet_event_year(srow.get("snippet") or "")
            if age is None or year is None:
                ok = False
                break
            srow["snippet"] = (
                f"In March {year}, the listing says the person, {age}, was {phrase} in {country}."
            )
        if not ok:
            used.discard(keys[hid])
            continue
        decision, code = base_of(hid)
        add(
            Case(
                "T17",
                hid,
                keys[hid],
                {"unchanged": True},
                forbid_de=decision != "DIFFERENT_ENTITY",
                base_decision=decision,
                base_code=code,
            )
        )
        n += 1

    # T18 drop the listing phrase or the tied country and the snippet must not supply a DOB
    n = 0
    for hid in store.hit_ids_sorted():
        if n >= PER_OP:
            break
        rows = snippet_rows(hid)
        if not rows or not take(hid):
            continue
        phrase = listing_phrase(store.hits[hid])
        for srow in rows:
            text = srow.get("snippet") or ""
            if phrase in text:
                text = text.replace(phrase, "mentioned in a filing")
            else:
                text = "No country is named in this filing."
            srow["snippet"] = text
        decision, code = base_of(hid)
        add(
            Case(
                "T18",
                hid,
                keys[hid],
                {"not_codes": ["DOB_MISMATCH", "NAME_DOB_MATCH", "NAME_DOB_LOCATION_MATCH"]},
                base_decision=decision,
                base_code=code,
            )
        )
        n += 1

    print(f"cases {len(cases)}", flush=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    save_bundle(bundle, WORK)
    out_path = os.path.join(OUT_DIR, "twin_output.jsonl")
    print("running system", flush=True)
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "system", "run"), WORK, out_path],
        check=False,
    )
    if proc.returncode != 0:
        print("system/run failed", proc.returncode)
        return proc.returncode
    got = {j["hit_id"]: j for j in load_jsonl(out_path)}
    report = score(cases, got, baseline, keys, used)
    with open(REPORT, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps({k: report[k] for k in ("cases", "passed", "unsafe", "untouched_changes")}, indent=2))
    for op, row in report["operators"].items():
        print(f"{op} {row['passed']}/{row['n']} unsafe {row['unsafe']}")
    return 0


def _snippet_event_year(snippet: str) -> Optional[int]:
    match = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(\d{4})|"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+(\d{4})|"
        r"(\d{4})",
        snippet,
        re.I,
    )
    if not match:
        return None
    token = next(group for group in match.groups() if group and group.isdigit() and len(group) == 4)
    return int(token)


def _same_country(raw: Any, country: str) -> bool:
    text = str(raw).split("[")[0].strip().lower()
    if text == country.lower():
        return True
    for alias in SPELLINGS.get(country, []):
        if text == alias.lower():
            return True
    return False


def passed(case: Case, row: Dict[str, Any]) -> bool:
    expect = case.expect
    if expect.get("unchanged"):
        return (row["decision"], row["reason_code"]) == (case.base_decision, case.base_code)
    if expect.get("decision") and row["decision"] != expect["decision"]:
        return False
    if expect.get("code") and row["reason_code"] != expect["code"]:
        return False
    if expect.get("not_code") and row["reason_code"] == expect["not_code"]:
        return False
    if expect.get("not_codes") and row["reason_code"] in expect["not_codes"]:
        return False
    if expect.get("record") and row.get("customer_record_id") != expect["record"]:
        return False
    return True


def score(cases, got, baseline, keys, used) -> Dict[str, Any]:
    ops: Dict[str, Any] = {}
    failures = []
    unsafe = []
    n_pass = 0
    for case in cases:
        row = got[case.hit_id]
        ok = passed(case, row)
        bad_clear = case.forbid_de and row["decision"] == "DIFFERENT_ENTITY"
        bucket = ops.setdefault(case.op, {"n": 0, "passed": 0, "unsafe": 0})
        bucket["n"] += 1
        if ok:
            n_pass += 1
            bucket["passed"] += 1
        else:
            toward_review = row["decision"] == "REVIEW"
            failures.append(
                {
                    "op": case.op,
                    "hit_id": case.hit_id,
                    "expect": case.expect,
                    "base": [case.base_decision, case.base_code],
                    "actual": [row["decision"], row["reason_code"]],
                    "toward_review": toward_review,
                    "note": case.note,
                }
            )
        if bad_clear:
            bucket["unsafe"] += 1
            unsafe.append(
                {
                    "op": case.op,
                    "hit_id": case.hit_id,
                    "actual": [row["decision"], row["reason_code"]],
                    "expect": case.expect,
                }
            )
    untouched = []
    case_hits = {c.hit_id for c in cases}
    for hid, before in baseline.items():
        if keys.get(hid) in used or hid in case_hits:
            continue
        after = got.get(hid)
        if after is None:
            continue
        if (before["decision"], before["reason_code"]) != (after["decision"], after["reason_code"]):
            untouched.append(
                {
                    "hit_id": hid,
                    "before": [before["decision"], before["reason_code"]],
                    "after": [after["decision"], after["reason_code"]],
                }
            )
    return {
        "cases": len(cases),
        "passed": n_pass,
        "unsafe": len(unsafe),
        "untouched_changes": len(untouched),
        "operators": ops,
        "failures": failures,
        "unsafe_cases": unsafe,
        "untouched": untouched[:50],
    }


if __name__ == "__main__":
    raise SystemExit(main())
