"""Issue 12: identical decisions across runs; shuffle → byte-identical output."""

from __future__ import annotations

import json
import random
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "data" / "screening" / "dev"
RUN = ROOT / "system" / "run"


@pytest.mark.skipif(not DEV.is_dir(), reason="dev data not unpacked")
def test_two_runs_same_decision_reason_code(tmp_path: Path) -> None:
    outs = []
    for i in range(2):
        out = tmp_path / f"r{i}.jsonl"
        subprocess.run(
            [sys.executable, str(RUN), str(DEV), str(out)],
            cwd=str(ROOT),
            check=True,
            env={
                **dict(**{k: v for k, v in __import__("os").environ.items()}),
                "PYTHONHASHSEED": "0",
            },
        )
        outs.append(out)
    a = [json.loads(ln) for ln in outs[0].read_text().splitlines() if ln.strip()]
    b = [json.loads(ln) for ln in outs[1].read_text().splitlines() if ln.strip()]
    assert [(x["hit_id"], x["decision"], x["reason_code"]) for x in a] == [
        (x["hit_id"], x["decision"], x["reason_code"]) for x in b
    ]


@pytest.mark.skipif(not DEV.is_dir(), reason="dev data not unpacked")
def test_shuffle_jsonl_byte_identical(tmp_path: Path) -> None:
    """Shuffling every JSONL must not change the output bytes."""
    import shutil

    shuffled = tmp_path / "shuffled"
    shutil.copytree(DEV, shuffled)
    rng = random.Random(0)
    for name in (
        "alerts.jsonl",
        "hits.jsonl",
        "customers.jsonl",
        "accounts.jsonl",
        "onboarding.jsonl",
        "kyc_checks.jsonl",
        "notes.jsonl",
        "search_results.jsonl",
    ):
        path = shuffled / name
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        rng.shuffle(lines)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    out_a = tmp_path / "a.jsonl"
    out_b = tmp_path / "b.jsonl"
    env = {**{k: v for k, v in __import__("os").environ.items()}, "PYTHONHASHSEED": "0"}
    subprocess.run(
        [sys.executable, str(RUN), str(DEV), str(out_a)], cwd=str(ROOT), check=True, env=env
    )
    subprocess.run(
        [sys.executable, str(RUN), str(shuffled), str(out_b)], cwd=str(ROOT), check=True, env=env
    )
    assert out_a.read_bytes() == out_b.read_bytes()
