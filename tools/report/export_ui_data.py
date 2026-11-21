"""Map engine traces (+ optional runs/summary.json) into ui/public/data/."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

DECISION_ORDER = {"REVIEW": 0, "SAME_ENTITY": 1, "DIFFERENT_ENTITY": 2}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace_dir", help="Directory of <hit_id>.json engine traces")
    parser.add_argument(
        "out_dir",
        nargs="?",
        default="ui/public/data",
        help="UI data directory (default: ui/public/data)",
    )
    parser.add_argument(
        "--summary",
        default="runs/summary.json",
        help="Optional runs/summary.json path",
    )
    args = parser.parse_args(argv)

    traces = _load_traces(args.trace_dir)
    if not traces:
        print(f"no traces in {args.trace_dir}", file=sys.stderr)
        return 1

    cases_dir = os.path.join(args.out_dir, "cases")
    os.makedirs(cases_dir, exist_ok=True)

    queue: List[Dict[str, Any]] = []
    for hit_id in sorted(traces):
        case = traces[hit_id]
        _write_json(os.path.join(cases_dir, f"{hit_id}.json"), case)
        queue.append(_queue_row(case))

    queue.sort(
        key=lambda row: (
            DECISION_ORDER.get(row["decision"], 9),
            row["alert_id"],
            row["hit_id"],
        )
    )
    _write_json(os.path.join(args.out_dir, "queue.json"), queue)

    summary_path = args.summary
    if os.path.isfile(summary_path):
        with open(summary_path, encoding="utf-8") as handle:
            summary = json.load(handle)
        _write_json(os.path.join(args.out_dir, "summary.json"), summary)
        print(f"wrote summary.json from {summary_path}")
    else:
        # Do not invent numbers; Run page shows "No run yet".
        print(f"no summary at {summary_path}; skipped summary.json")

    print(f"wrote {len(queue)} cases → {args.out_dir}")
    return 0


def _load_traces(trace_dir: str) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    if not os.path.isdir(trace_dir):
        return out
    for name in sorted(os.listdir(trace_dir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(trace_dir, name)
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
        hit_id = payload.get("hit_id") or name[:-5]
        out[hit_id] = payload
    return out


def _queue_row(case: Dict[str, Any]) -> Dict[str, Any]:
    profile = case.get("profile") or {}
    name_block = profile.get("name") or {}
    return {
        "hit_id": case.get("hit_id"),
        "alert_id": case.get("alert_id"),
        "customer_name": case.get("customer_name") or "Unknown",
        "customer_country_iso2": case.get("customer_country_iso2"),
        "listed_name": name_block.get("display") or "",
        "listed_country_iso2": name_block.get("country_iso2"),
        "category": profile.get("category") or "",
        "decision": case.get("decision") or "REVIEW",
        "reason_code": case.get("reason_code") or "INSUFFICIENT_DATA",
    }


def _write_json(path: str, payload: Any) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
