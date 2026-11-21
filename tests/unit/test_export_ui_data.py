"""export_ui_data maps traces into ui/public/data without inventing run numbers."""

from __future__ import annotations

import json
from pathlib import Path

from tools.report.export_ui_data import main


def test_export_ui_data_writes_queue_and_cases(tmp_path: Path) -> None:
    traces = tmp_path / "traces"
    traces.mkdir()
    case = {
        "hit_id": "H-AAAAAA",
        "alert_id": "A-AAAAAA",
        "customer_name": "Ada Lovelace",
        "customer_country_iso2": "br",
        "decision": "SAME_ENTITY",
        "reason_code": "NAME_DOB_LOCATION_MATCH",
        "profile": {
            "category": "PEP",
            "name": {"display": "LOVELACE, ADA", "country_iso2": "br"},
        },
        "output_line": {"hit_id": "H-AAAAAA"},
    }
    (traces / "H-AAAAAA.json").write_text(json.dumps(case), encoding="utf-8")
    out = tmp_path / "ui-data"
    assert main([str(traces), str(out), "--summary", str(tmp_path / "missing.json")]) == 0
    queue = json.loads((out / "queue.json").read_text(encoding="utf-8"))
    assert len(queue) == 1
    assert queue[0]["hit_id"] == "H-AAAAAA"
    assert queue[0]["customer_country_iso2"] == "br"
    saved = json.loads((out / "cases" / "H-AAAAAA.json").read_text(encoding="utf-8"))
    assert saved["hit_id"] == "H-AAAAAA"
    assert not (out / "summary.json").exists()


def test_export_copies_summary_when_present(tmp_path: Path) -> None:
    traces = tmp_path / "traces"
    traces.mkdir()
    (traces / "H-AAAAAA.json").write_text(
        json.dumps(
            {
                "hit_id": "H-AAAAAA",
                "alert_id": "A-AAAAAA",
                "customer_name": "Ada",
                "decision": "REVIEW",
                "reason_code": "INSUFFICIENT_DATA",
                "profile": {"category": "PEP", "name": {"display": "ADA"}},
            }
        ),
        encoding="utf-8",
    )
    summary = {
        "hits": 1,
        "unsafe_practice": 0,
        "practice_labels": 1,
        "identical_runs": 5,
        "runs": 5,
        "seconds": 1.0,
        "cost_usd": 0.0,
        "split": {"DIFFERENT_ENTITY": 0, "SAME_ENTITY": 0, "REVIEW": 1},
    }
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    out = tmp_path / "ui-data"
    assert main([str(traces), str(out), "--summary", str(summary_path)]) == 0
    saved = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert saved["hits"] == 1
    assert saved["unsafe_practice"] == 0
