"""NAMESAKE_TRACE_DIR writes CasePage JSON without changing output bytes."""

from __future__ import annotations

import json
import os
from pathlib import Path

from namesake.countries import iso2_for_country
from namesake.pipeline import run_pipeline, set_engine
from namesake.schema import make_line


def _write_world(data: Path) -> None:
    data.mkdir(parents=True, exist_ok=True)
    (data / "alerts.jsonl").write_text(
        json.dumps(
            {
                "alert_id": "A-AAAAAA",
                "screened_at": "2026-01-15",
                "customer": {
                    "name": "Ada Lovelace",
                    "dob": "1985-09-12",
                    "country": "Brazil",
                    "entity_type": "Individual",
                },
                "account_ref": "ACC-AAAAAA",
                "login_handle": None,
                "email": None,
                "hit_ids": ["H-AAAAAA"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (data / "hits.jsonl").write_text(
        json.dumps(
            {
                "hit_id": "H-AAAAAA",
                "alert_id": "A-AAAAAA",
                "name": "LOVELACE, ADA",
                "entity_type": "Individual",
                "dobs": ["1985"],
                "aliases": [],
                "countries": ["Brazil"],
                "nationality": ["Brazilian"],
                "addresses": [],
                "categories": ["PEP"],
                "primary_category": "PEP",
                "match_score": 100,
                "profile_notes": None,
                "deceased_date": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (data / "customers.jsonl").write_text(
        json.dumps(
            {
                "record_id": "CUS-000001",
                "full_name": "Ada Lovelace",
                "preferred_name": "Ada Lovelace",
                "login_name": "ada",
                "dob": "1985-09-12",
                "residence_country": "Brazil",
                "nationality": "Brazilian",
                "entity_type": "Individual",
                "phone": "+5511999999999",
                "email": "ada@example.test",
                "city": "Sao Paulo",
                "address": "Sao Paulo, Brazil",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (data / "accounts.jsonl").write_text(
        json.dumps(
            {
                "account_id": "ACC-AAAAAA",
                "customer_id": "CUS-000001",
                "login_handle": "ada",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    for name in ("onboarding", "kyc_checks", "notes", "search_results"):
        (data / f"{name}.jsonl").write_text("", encoding="utf-8")
    (data / "name_variants.json").write_text(
        json.dumps({"groups": [], "company_legal_forms": ["Ltd", "LLC"]}),
        encoding="utf-8",
    )


def test_iso2_for_country() -> None:
    assert iso2_for_country("Brazil") == "br"
    assert iso2_for_country("United Kingdom") == "gb"
    assert iso2_for_country(None) is None


def test_trace_json_written_without_changing_output(tmp_path: Path) -> None:
    data = tmp_path / "world"
    _write_world(data)
    out_a = tmp_path / "a.jsonl"
    out_b = tmp_path / "b.jsonl"
    traces = tmp_path / "traces"

    # Baseline without traces
    os.environ.pop("NAMESAKE_TRACE_DIR", None)
    run_pipeline(str(data), str(out_a))

    os.environ["NAMESAKE_TRACE_DIR"] = str(traces)
    try:
        run_pipeline(str(data), str(out_b))
    finally:
        os.environ.pop("NAMESAKE_TRACE_DIR", None)

    assert out_a.read_bytes() == out_b.read_bytes()
    trace_path = traces / "H-AAAAAA.json"
    assert trace_path.is_file()
    payload = json.loads(trace_path.read_text(encoding="utf-8"))
    assert payload["hit_id"] == "H-AAAAAA"
    assert payload["alert_id"] == "A-AAAAAA"
    assert payload["found_via"]["kind"] == "account"
    assert payload["found_via"]["id"] == "ACC-AAAAAA"
    assert payload["decision"] in {"DIFFERENT_ENTITY", "SAME_ENTITY", "REVIEW"}
    assert "output_line" in payload
    assert payload["output_line"]["hit_id"] == "H-AAAAAA"
    assert "ladder" in payload
    assert "links" in payload
    assert payload["customer_country_iso2"] == "br"
    # Trace keys must not leak into the submitted line
    row = json.loads(out_b.read_text(encoding="utf-8").splitlines()[0])
    assert "_namesake_trace" not in row
    assert "_namesake_engine_trace" not in row


def test_trace_on_engine_exception(tmp_path: Path) -> None:
    data = tmp_path / "world"
    _write_world(data)
    traces = tmp_path / "traces"
    out = tmp_path / "out.jsonl"

    def boom(store, hit_id):  # noqa: ANN001
        raise RuntimeError("boom")

    set_engine(boom)
    os.environ["NAMESAKE_TRACE_DIR"] = str(traces)
    try:
        run_pipeline(str(data), str(out))
    finally:
        os.environ.pop("NAMESAKE_TRACE_DIR", None)
        set_engine(None)

    payload = json.loads((traces / "H-AAAAAA.json").read_text(encoding="utf-8"))
    assert payload["decision"] == "REVIEW"
    assert "error" in payload
    row = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    assert row == make_line(
        "H-AAAAAA",
        "A-AAAAAA",
        "REVIEW",
        "INSUFFICIENT_DATA",
        None,
        row["reason"],
        ["A-AAAAAA"],
    ) or row["decision"] == "REVIEW"
