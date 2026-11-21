"""Load a data folder and build lookup indexes. Never scan 72k customers per hit."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from namesake.io_util import load_json, read_jsonl


class DataStore:
    """In-memory screening data + indexes."""

    def __init__(self, data_folder: str) -> None:
        self.root = os.path.abspath(data_folder)
        self.alerts: Dict[str, Dict[str, Any]] = {}
        self.hits: Dict[str, Dict[str, Any]] = {}
        self.customers: Dict[str, Dict[str, Any]] = {}
        self.accounts: List[Dict[str, Any]] = []
        self.onboarding: List[Dict[str, Any]] = []
        self.kyc_checks: List[Dict[str, Any]] = []
        self.notes: List[Dict[str, Any]] = []
        self.search_results: List[Dict[str, Any]] = []
        self.name_variants: Dict[str, Any] = {}

        # indexes
        self.account_holders: Dict[str, List[str]] = {}  # account_id -> [customer_id…]
        self.login_to_accounts: Dict[str, List[str]] = {}
        self.email_to_customers: Dict[str, List[str]] = {}
        self.phone_to_customers: Dict[str, List[str]] = {}
        self.doc_to_checks: Dict[str, List[Dict[str, Any]]] = {}
        self.applicant_to_checks: Dict[str, List[Dict[str, Any]]] = {}
        self.customer_to_onboarding: Dict[str, List[Dict[str, Any]]] = {}
        self.account_to_onboarding: Dict[str, List[Dict[str, Any]]] = {}
        self.email_to_notes: Dict[str, List[Dict[str, Any]]] = {}
        self.query_to_search: Dict[str, List[Dict[str, Any]]] = {}
        self.alert_hits: Dict[str, List[str]] = {}

        self._load()

    def _load(self) -> None:
        root = self.root
        for row in read_jsonl(os.path.join(root, "alerts.jsonl")):
            self.alerts[row["alert_id"]] = row
            self.alert_hits[row["alert_id"]] = list(row.get("hit_ids") or [])
        for row in read_jsonl(os.path.join(root, "hits.jsonl")):
            self.hits[row["hit_id"]] = row
        for row in read_jsonl(os.path.join(root, "customers.jsonl")):
            self.customers[row["record_id"]] = row
            email = (row.get("email") or "").strip().lower()
            if email:
                self.email_to_customers.setdefault(email, []).append(row["record_id"])
            phone = _norm_phone(row.get("phone"))
            if phone:
                self.phone_to_customers.setdefault(phone, []).append(row["record_id"])

        self.accounts = read_jsonl(os.path.join(root, "accounts.jsonl"))
        for row in self.accounts:
            aid = row["account_id"]
            self.account_holders.setdefault(aid, []).append(row["customer_id"])
            login = (row.get("login_handle") or "").strip().lower()
            if login:
                self.login_to_accounts.setdefault(login, []).append(aid)

        self.onboarding = read_jsonl(os.path.join(root, "onboarding.jsonl"))
        for row in self.onboarding:
            self.customer_to_onboarding.setdefault(row["customer_id"], []).append(row)
            self.account_to_onboarding.setdefault(row["account_id"], []).append(row)

        self.kyc_checks = read_jsonl(os.path.join(root, "kyc_checks.jsonl"))
        for row in self.kyc_checks:
            self.applicant_to_checks.setdefault(row["applicant_id"], []).append(row)
            doc = (row.get("document_number") or "").strip().upper()
            if doc:
                self.doc_to_checks.setdefault(doc, []).append(row)

        self.notes = read_jsonl(os.path.join(root, "notes.jsonl"))
        for row in self.notes:
            email = (row.get("requester_email") or "").strip().lower()
            if email:
                self.email_to_notes.setdefault(email, []).append(row)

        self.search_results = read_jsonl(os.path.join(root, "search_results.jsonl"))
        for row in self.search_results:
            q = (row.get("query") or "").strip().lower()
            self.query_to_search.setdefault(q, []).append(row)

        nv_path = os.path.join(root, "name_variants.json")
        if os.path.isfile(nv_path):
            self.name_variants = load_json(nv_path)

    def hit_ids_sorted(self) -> List[str]:
        return sorted(self.hits.keys())

    def alert_for_hit(self, hit_id: str) -> Optional[Dict[str, Any]]:
        hit = self.hits.get(hit_id)
        if not hit:
            return None
        return self.alerts.get(hit.get("alert_id", ""))


def _norm_phone(raw: Optional[str]) -> str:
    if not raw:
        return ""
    return "".join(ch for ch in raw if ch.isdigit())
