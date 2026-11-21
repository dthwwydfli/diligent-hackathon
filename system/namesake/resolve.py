"""[A] Customer resolution: link walk, unlinked fit, P3 union-find merge, verified facts."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from namesake.countries import canonical_country, is_unmappable_place
from namesake.dates import DateInterval, parse_date
from namesake.facts import CERTAIN, Fact, Person
from namesake.names import build_variant_map, names_agree
from namesake.store import DataStore


class UnionFind:
    def __init__(self) -> None:
        self.parent: Dict[str, str] = {}

    def add(self, x: str) -> None:
        self.parent.setdefault(x, x)

    def find(self, x: str) -> str:
        self.add(x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            # Deterministic: smaller id wins
            if ra < rb:
                self.parent[rb] = ra
            else:
                self.parent[ra] = rb

    def components(self, members: Set[str]) -> List[List[str]]:
        groups: Dict[str, List[str]] = {}
        for m in sorted(members):
            groups.setdefault(self.find(m), []).append(m)
        return [groups[k] for k in sorted(groups)]


def _variants(store: DataStore) -> Dict[str, Set[str]]:
    groups = store.name_variants.get("groups") or []
    return build_variant_map(groups)


def _legal_forms(store: DataStore) -> List[str]:
    return list(store.name_variants.get("company_legal_forms") or [])


def _screened(alert: Dict[str, Any]) -> Dict[str, Any]:
    return alert.get("customer") or {}


def _record_name_agrees(
    record: Dict[str, Any],
    screened_name: Optional[str],
    variants: Dict[str, Set[str]],
    forms: List[str],
) -> bool:
    if not screened_name:
        return True
    is_co = (record.get("entity_type") or "").lower() == "company"
    for key in ("full_name", "preferred_name", "login_name"):
        if names_agree(
            record.get(key),
            screened_name,
            variants=variants,
            company_legal_forms=forms if is_co else None,
            a_is_company=is_co,
            b_is_company=is_co,
        ):
            return True
    return False


def _dob_agrees_parts(record_dob: Optional[str], screened_dob: Optional[str]) -> bool:
    if not screened_dob:
        return True
    if not record_dob:
        return False
    a = parse_date(record_dob)
    b = parse_date(screened_dob)
    if a is None or b is None:
        return False
    from namesake.dates import intervals_agree

    return intervals_agree(a, b)


def _country_fits(record: Dict[str, Any], screened_country: Optional[str]) -> bool:
    if not screened_country:
        return True
    want = canonical_country(screened_country)
    if not want:
        return False
    for key in ("residence_country", "nationality"):
        got = canonical_country(record.get(key))
        if got == want:
            return True
    return False


def _city_fits(record: Dict[str, Any], screened_city: Optional[str]) -> bool:
    if not screened_city:
        return True
    needle = screened_city.strip().lower()
    city = (record.get("city") or "").lower()
    address = (record.get("address") or "").lower()
    return needle in city or needle in address


def record_fits_screened(
    record: Dict[str, Any],
    screened: Dict[str, Any],
    variants: Dict[str, Set[str]],
    forms: List[str],
) -> bool:
    """Unlinked fit: every screened detail present agrees (P2)."""
    if not _record_name_agrees(record, screened.get("name"), variants, forms):
        return False
    if not _dob_agrees_parts(record.get("dob"), screened.get("dob")):
        return False
    if not _country_fits(record, screened.get("country")):
        return False
    if not _city_fits(record, screened.get("city")):
        return False
    return True


def _seed_from_link(store: DataStore, alert: Dict[str, Any]) -> List[str]:
    seeds: List[str] = []
    account_ref = alert.get("account_ref")
    if account_ref:
        seeds.extend(store.account_holders.get(account_ref, []))
    login = (alert.get("login_handle") or "").strip().lower()
    if login:
        for aid in store.login_to_accounts.get(login, []):
            seeds.extend(store.account_holders.get(aid, []))
    email = (alert.get("email") or "").strip().lower()
    if email:
        seeds.extend(store.email_to_customers.get(email, []))
    # unique, stable
    out: List[str] = []
    seen: Set[str] = set()
    for s in seeds:
        if s not in seen and s in store.customers:
            seen.add(s)
            out.append(s)
    return out


def _merge_closure(store: DataStore, seeds: List[str]) -> List[List[str]]:
    """Union-find over phone+full-DOB and approved-doc-number edges; keep components touching seeds."""
    if not seeds:
        return []
    uf = UnionFind()
    for s in seeds:
        uf.add(s)

    # Phone + full DOB edges among customers that share a phone with any seed-reachable set.
    # Grow: start from seeds, add anyone sharing a merge edge with the current set.
    frontier = set(seeds)
    members = set(seeds)
    while frontier:
        nxt: Set[str] = set()
        for cid in frontier:
            rec = store.customers.get(cid)
            if not rec:
                continue
            phone = "".join(ch for ch in (rec.get("phone") or "") if ch.isdigit())
            dob = parse_date(rec.get("dob"))
            from namesake.dates import precise_day

            # Full DOB = day precision (P3: same full date of birth)
            is_full = dob is not None and precise_day(dob) is not None
            if phone and is_full and dob is not None:
                for other_id in store.phone_to_customers.get(phone, []):
                    if other_id == cid:
                        continue
                    other = store.customers.get(other_id)
                    if not other:
                        continue
                    od = parse_date(other.get("dob"))
                    if (
                        od
                        and precise_day(od) is not None
                        and od.y_lo == dob.y_lo
                        and od.m_lo == dob.m_lo
                        and od.d_lo == dob.d_lo
                    ):
                        uf.union(cid, other_id)
                        if other_id not in members:
                            nxt.add(other_id)
                            members.add(other_id)

            # Document-number edges via approved KYC linked through onboarding
            for ob in store.customer_to_onboarding.get(cid, []):
                app = ob.get("kyc_applicant_id")
                if not app:
                    continue
                for check in store.applicant_to_checks.get(app, []):
                    if (check.get("result") or "").lower() != "approved":
                        continue
                    doc = (check.get("document_number") or "").strip().upper()
                    if not doc:
                        continue
                    for other_check in store.doc_to_checks.get(doc, []):
                        if (other_check.get("result") or "").lower() != "approved":
                            continue
                        other_app = other_check.get("applicant_id")
                        # find customers with this applicant
                        for ob2 in store.onboarding:
                            if ob2.get("kyc_applicant_id") == other_app:
                                oid = ob2.get("customer_id")
                                if oid and oid != cid:
                                    uf.union(cid, oid)
                                    if oid not in members:
                                        nxt.add(oid)
                                        members.add(oid)
        frontier = nxt

    return uf.components(members)


def _approved_checks_for_records(
    store: DataStore, record_ids: List[str]
) -> List[Tuple[str, Dict[str, Any]]]:
    """Return (source_id, normalized check dict) sorted by date desc (I5)."""
    from namesake.readers import read_kyc_note, read_residence_note

    items: List[Tuple[str, str, Dict[str, Any]]] = []
    for cid in record_ids:
        for ob in store.customer_to_onboarding.get(cid, []):
            app = ob.get("kyc_applicant_id")
            if not app:
                continue
            for check in store.applicant_to_checks.get(app, []):
                if (check.get("result") or "").lower() != "approved":
                    continue
                items.append(
                    (
                        check.get("checked_at") or "",
                        check["check_id"],
                        {
                            "verified_name": check.get("verified_name"),
                            "verified_dob": check.get("verified_dob"),
                            "document_country": check.get("document_country"),
                            "kind": "kyc",
                            "at": check.get("checked_at") or "",
                        },
                    )
                )
        rec = store.customers.get(cid) or {}
        email = (rec.get("email") or "").strip().lower()
        if not email:
            continue
        for note in store.email_to_notes.get(email, []):
            channel = (note.get("channel") or "").lower()
            text = note.get("text") or ""
            if channel == "kyc":
                ext = read_kyc_note(text, note.get("created_at") or "")
                if ext.approved is False:
                    continue
                llm = getattr(store, "llm", None)
                llm_payload = llm.second_opinion(text) if llm is not None else None
                from namesake.llm import llm_fact, llm_negative

                # LLM veto: a rejected/failed/expired check is never verified identity.
                if llm_negative(llm_payload):
                    continue
                filled_uncertain = False
                if not ext.verified_name:
                    filled = llm_fact(llm_payload, "name")
                    if filled:
                        ext.verified_name = filled
                        filled_uncertain = True
                if ext.dob is None:
                    filled = llm_fact(llm_payload, "dob")
                    if filled:
                        iv = parse_date(filled)
                        if iv is not None:
                            ext.dob = DateInterval(
                                iv.y_lo,
                                iv.m_lo,
                                iv.d_lo,
                                iv.y_hi,
                                iv.m_hi,
                                iv.d_hi,
                                certain=False,
                                source=iv.source,
                            )
                            filled_uncertain = True
                if not ext.document_country:
                    filled = llm_fact(llm_payload, "country")
                    if filled:
                        c = canonical_country(filled)
                        if c:
                            ext.document_country = c
                            filled_uncertain = True
                if ext.approved is True and (ext.dob or ext.verified_name):
                    certain = (
                        False
                        if filled_uncertain
                        else (
                            ext.certain
                            or (ext.dob is not None and ext.verified_name is not None)
                        )
                    )
                    items.append(
                        (
                            note.get("created_at") or "",
                            note["note_id"],
                            {
                                "verified_name": ext.verified_name,
                                "verified_dob": None,
                                "verified_dob_interval": ext.dob,
                                "document_country": ext.document_country,
                                "kind": "note",
                                "at": note.get("created_at") or "",
                                # LLM-filled gaps stay uncertain and cannot clear.
                                "certain": certain,
                            },
                        )
                    )
                elif ext.approved is None:
                    # I10: unclear polarity — not evidence; may mark unknown later
                    pass
            else:
                # Residence notes enrich country set
                res = read_residence_note(text)
                if res.countries_lived or res.open_country_set:
                    items.append(
                        (
                            note.get("created_at") or "",
                            note["note_id"],
                            {
                                "kind": "residence",
                                "countries_lived": list(res.countries_lived),
                                "open_country_set": res.open_country_set,
                            },
                        )
                    )
    # Date, then id. File order must not decide a tie (shuffle test).
    items.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [(sid, obj) for _, sid, obj in items]


def _latest_parsed_at(approved: List[Tuple[str, Dict[str, Any]]]) -> str:
    """Timestamp of the newest approved check that actually yielded a name and a DOB."""
    latest = ""
    for _source_id, check in approved:
        if check.get("kind") == "residence":
            continue
        name = check.get("verified_name")
        dob = check.get("verified_dob_interval")
        if dob is None:
            dob = check.get("verified_dob")
        if name and dob:
            at = check.get("at") or ""
            if at > latest:
                latest = at
    return latest


def _newer_unread_kyc_note(
    store: DataStore, record_ids: List[str], latest_parsed_at: str
) -> Optional[str]:
    """Non-negative KYC note newer than the last parsed check, with no name and DOB taken from it."""
    from namesake.readers import read_kyc_note

    found_id: Optional[str] = None
    found_at = ""
    for cid in record_ids:
        rec = store.customers.get(cid) or {}
        email = (rec.get("email") or "").strip().lower()
        if not email:
            continue
        for note in store.email_to_notes.get(email, []):
            if (note.get("channel") or "").lower() != "kyc":
                continue
            created = note.get("created_at") or ""
            if created <= latest_parsed_at:
                continue
            text = note.get("text") or ""
            ext = read_kyc_note(text, created)
            if ext.approved is False:
                continue
            if ext.verified_name and ext.dob is not None:
                continue
            note_id = note.get("note_id") or ""
            if found_id is None or created > found_at or (created == found_at and note_id < found_id):
                found_at = created
                found_id = note_id
    return found_id


def _forget_verified_identity(person: Person, note_id: str) -> None:
    """Verified name, DOB and document country are unknown. Declared facts must not clear or confirm."""
    person.identity_unknown = True
    person.dob_unknown = True
    person.dob = None
    person.verified_dob = None
    person.verified_name = None
    person.verified_doc_country = None
    person.has_approved_check = False
    if person.verified_source and person.verified_source in person.evidence_ids:
        person.evidence_ids.remove(person.verified_source)
    person.verified_source = None
    person.countries = {fact.value for fact in person.country_facts}
    if note_id and note_id not in person.evidence_ids:
        person.evidence_ids.append(note_id)


def build_person(store: DataStore, record_ids: List[str], screened: Dict[str, Any]) -> Person:
    person = Person(record_ids=sorted(record_ids), evidence_ids=sorted(record_ids))
    dobs: List[DateInterval] = []
    for cid in person.record_ids:
        rec = store.customers[cid]
        person.entity_type = rec.get("entity_type") or person.entity_type
        for key in ("full_name", "preferred_name"):
            if rec.get(key):
                person.names.append(Fact("name", rec[key], cid, key, CERTAIN))
        for key in ("residence_country", "nationality"):
            raw = rec.get(key)
            c = canonical_country(raw)
            if c:
                person.countries.add(c)
                person.country_facts.append(Fact("country", c, cid, key, CERTAIN))
            elif is_unmappable_place(raw):
                person.countries_open = True
        iv = parse_date(rec.get("dob"), source=cid)
        if iv:
            dobs.append(iv)
            person.dob_facts.append(Fact("dob", iv, cid, "dob", CERTAIN if iv.certain else "U"))

    screened_name = screened.get("name")
    person.screened_name = screened_name

    # Verified from most recent approved KYC / KYC note (I5); residence notes enrich countries
    approved = _approved_checks_for_records(store, person.record_ids)
    verified_picked = False
    for source_id, check in approved:
        kind = check.get("kind")
        if kind == "residence":
            for c in check.get("countries_lived") or []:
                person.countries.add(c)
                person.country_facts.append(Fact("country", c, source_id, "note", CERTAIN))
            if check.get("open_country_set"):
                person.countries_open = True
            if source_id not in person.evidence_ids:
                person.evidence_ids.append(source_id)
            continue
        if verified_picked:
            continue
        # Skip uncertain notes for enabling clearance facts (still may set unknown)
        if kind == "note" and check.get("certain") is False:
            continue
        person.has_approved_check = True
        person.verified_source = source_id
        person.verified_name = check.get("verified_name")
        if check.get("verified_dob_interval") is not None:
            person.verified_dob = check["verified_dob_interval"]
        else:
            person.verified_dob = parse_date(check.get("verified_dob"), source=source_id)
        doc_raw = check.get("document_country")
        person.verified_doc_country = canonical_country(doc_raw)
        if person.verified_doc_country:
            person.countries.add(person.verified_doc_country)
        elif is_unmappable_place(doc_raw):
            person.countries_open = True
        if source_id not in person.evidence_ids:
            person.evidence_ids.append(source_id)
        verified_picked = True

    # A newer KYC note we could not read must not fall back to an older check or the declared record.
    blocking_note = _newer_unread_kyc_note(
        store, person.record_ids, _latest_parsed_at(approved)
    )
    if blocking_note:
        _forget_verified_identity(person, blocking_note)

    if person.identity_unknown:
        person.dob = None
        person.dob_unknown = True
    elif person.verified_dob is not None:
        person.dob = person.verified_dob
    elif dobs:
        # I6: conflicting declared DOBs → UNKNOWN
        years = {(d.y_lo, d.y_hi, precise_key(d)) for d in dobs}
        if len(years) > 1:
            person.dob_unknown = True
            person.dob = None
        else:
            person.dob = dobs[0]
    return person


def precise_key(iv: DateInterval) -> Tuple:
    from namesake.dates import precise_day, precise_month

    return (iv.y_lo, precise_month(iv), precise_day(iv))


def resolve_customers(store: DataStore, alert: Dict[str, Any]) -> List[Person]:
    """Return zero or more Person objects for the alert."""
    screened = _screened(alert)
    variants = _variants(store)
    forms = _legal_forms(store)
    seeds = _seed_from_link(store, alert)

    if seeds:
        components = _merge_closure(store, seeds)
        # If link leads to more than one person, screened details choose (P2)
        persons = [build_person(store, comp, screened) for comp in components]
        if len(persons) > 1:
            chosen = [
                p
                for p in persons
                if any(
                    record_fits_screened(store.customers[rid], screened, variants, forms)
                    for rid in p.record_ids
                )
            ]
            if chosen:
                return chosen
            return persons
        return persons

    # Unlinked: index-assisted search (no full customer scan)
    candidates: Set[str] = set()
    dob = screened.get("dob")
    if not hasattr(store, "_dob_year_index"):
        idx: Dict[int, List[str]] = {}
        for cid, rec in store.customers.items():
            iv = parse_date(rec.get("dob"))
            if iv:
                for y in iv.years():
                    idx.setdefault(y, []).append(cid)
        store._dob_year_index = idx  # type: ignore[attr-defined]

    if dob:
        iv = parse_date(dob)
        if iv:
            for y in iv.years():
                for cid in store._dob_year_index.get(y, []):  # type: ignore[attr-defined]
                    candidates.add(cid)

    fits = [
        cid
        for cid in sorted(candidates)
        if record_fits_screened(store.customers[cid], screened, variants, forms)
    ]
    if not fits:
        return []
    components = _merge_closure(store, fits)
    # If several records fit and merge into one person → one person, not AMBIGUOUS
    return [build_person(store, comp, screened) for comp in components]
