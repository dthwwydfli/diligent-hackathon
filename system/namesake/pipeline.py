"""End-to-end run: one valid line per hit, always."""

from __future__ import annotations

import json
import os
import traceback
from typing import Any, Dict, List, Optional

from namesake.io_util import write_jsonl
from namesake.schema import make_line
from namesake.store import DataStore


def run_pipeline(data_folder: str, output_file: str) -> None:
    store = DataStore(data_folder)
    trace_dir = os.environ.get("NAMESAKE_TRACE_DIR")
    rows: List[Dict[str, Any]] = []
    for hit_id in store.hit_ids_sorted():
        hit = store.hits[hit_id]
        alert_id = hit.get("alert_id") or "A-000000"
        case_trace: Optional[Dict[str, Any]] = None
        engine_trace: Optional[Dict[str, Any]] = None
        try:
            row = decide_hit(store, hit_id)
            if isinstance(row, dict):
                case_trace = row.pop("_namesake_trace", None)
                engine_trace = row.pop("_namesake_engine_trace", None)
        except Exception:
            row = make_line(
                hit_id=hit_id,
                alert_id=alert_id,
                decision="REVIEW",
                reason_code="INSUFFICIENT_DATA",
                customer_record_id=None,
                reason=(
                    "Processing this hit failed, so it was left for review. "
                    "The other hits in the run were not affected."
                ),
                evidence=[alert_id],
            )
            if trace_dir:
                case_trace = {
                    "hit_id": hit_id,
                    "alert_id": alert_id,
                    "error": traceback.format_exc(),
                    "decision": "REVIEW",
                    "reason_code": "INSUFFICIENT_DATA",
                    "output_line": dict(row),
                }
        if trace_dir:
            payload = case_trace or engine_trace or {"hit_id": hit_id, "output_line": dict(row)}
            _write_trace(trace_dir, hit_id, payload)
        rows.append(row)
    write_jsonl(output_file, rows)


def decide_hit(store: DataStore, hit_id: str) -> Dict[str, Any]:
    """Decide one hit via the proof engine (or a test override)."""
    engine = getattr(decide_hit, "_engine", None)
    if engine is not None:
        return engine(store, hit_id)

    from namesake.engine import decide

    return decide(store, hit_id)


def set_engine(fn: Optional[Any]) -> None:
    """Test / later wiring hook."""
    decide_hit._engine = fn  # type: ignore[attr-defined]


def _write_trace(trace_dir: str, hit_id: str, payload: Dict[str, Any]) -> None:
    os.makedirs(trace_dir, exist_ok=True)
    path = os.path.join(trace_dir, f"{hit_id}.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
