"""Print practice scorecard for a run."""

from __future__ import annotations

import json
import os
import sys
from typing import List

COST = {
    "DIFFERENT_ENTITY": {"DIFFERENT_ENTITY": 0, "SAME_ENTITY": 3, "REVIEW": 3},
    "SAME_ENTITY": {"DIFFERENT_ENTITY": 60, "SAME_ENTITY": 0, "REVIEW": 2},
    "REVIEW": {"DIFFERENT_ENTITY": 60, "SAME_ENTITY": 2, "REVIEW": 0},
}


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print("usage: scorecard.py <output.jsonl> [practice_labels.jsonl]")
        return 2
    output = argv[0]
    practice = argv[1] if len(argv) > 1 else "data/screening/dev/practice_labels.jsonl"
    with open(output, encoding="utf-8") as handle:
        answers = {json.loads(ln)["hit_id"]: json.loads(ln) for ln in handle if ln.strip()}
    with open(practice, encoding="utf-8") as handle:
        labels = [json.loads(ln) for ln in handle if ln.strip()]
    cost = sum(
        COST[row["decision"]][answers.get(row["hit_id"], {}).get("decision", "REVIEW")]
        for row in labels
    )
    baseline = sum(COST[row["decision"]]["REVIEW"] for row in labels)
    right = [
        row for row in labels if answers.get(row["hit_id"], {}).get("decision") == row["decision"]
    ]
    unsafe = sum(
        1
        for row in labels
        if row["decision"] != "DIFFERENT_ENTITY"
        and answers.get(row["hit_id"], {}).get("decision") == "DIFFERENT_ENTITY"
    )
    print(f"practice: {len(right)}/{len(labels)} right, {unsafe} unsafe clearances")
    print(f"decision score {100 * max(0.0, 1 - cost / baseline):.1f}")
    print(f"LLM: OPENROUTER_API_KEY set={bool(os.environ.get('OPENROUTER_API_KEY'))}")
    return 0 if unsafe == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
