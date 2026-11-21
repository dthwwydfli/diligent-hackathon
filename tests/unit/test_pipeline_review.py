"""Issue 1 gate: all-REVIEW writer, validate.py, determinism, isolation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "data" / "screening" / "dev"
VALIDATE = ROOT / "vendor" / "organiser" / "validate.py"
RUN = ROOT / "system" / "run"


@pytest.mark.skipif(not DEV.is_dir(), reason="dev data not unpacked")
def test_run_validate_one_line_per_hit(tmp_path: Path) -> None:
    """Issue 1/7: validate.py exits 0; 819 lines; schema-valid decisions."""
    out = tmp_path / "out.jsonl"
    proc = subprocess.run(
        [sys.executable, str(RUN), str(DEV), str(out)],
        cwd=str(ROOT / "system"),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 819
    for ln in lines:
        row = json.loads(ln)
        assert row["decision"] in {"DIFFERENT_ENTITY", "SAME_ENTITY", "REVIEW"}

    val = subprocess.run(
        [
            sys.executable,
            str(VALIDATE),
            "--data",
            str(DEV),
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert val.returncode == 0, val.stdout + val.stderr


@pytest.mark.skipif(not DEV.is_dir(), reason="dev data not unpacked")
def test_two_runs_byte_identical(tmp_path: Path) -> None:
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    for path in (a, b):
        subprocess.run(
            [sys.executable, str(RUN), str(DEV), str(path)],
            cwd=str(ROOT),
            check=True,
        )
    assert a.read_bytes() == b.read_bytes()


def test_malformed_alert_isolated(tmp_path: Path) -> None:
    """One bad alert → REVIEW line; run continues (SPEC §5.8)."""
    from namesake.pipeline import run_pipeline, set_engine
    from namesake.store import DataStore

    # Build a tiny synthetic world
    data = tmp_path / "world"
    data.mkdir()
    (data / "alerts.jsonl").write_text(
        json.dumps(
            {
                "alert_id": "A-AAAAAA",
                "screened_at": "2026-01-01",
                "customer": {"name": "Ada", "entity_type": "Individual"},
                "account_ref": None,
                "login_handle": None,
                "email": None,
                "hit_ids": ["H-AAAAAA", "H-BBBBBB"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    hits = [
        {
            "hit_id": "H-AAAAAA",
            "alert_id": "A-AAAAAA",
            "name": "Ada",
            "entity_type": "Individual",
            "dobs": [],
            "aliases": [],
            "countries": [],
            "addresses": [],
            "categories": [],
            "profile_notes": None,
            "deceased_date": None,
        },
        {
            "hit_id": "H-BBBBBB",
            "alert_id": "A-AAAAAA",
            "name": "Bob",
            "entity_type": "Individual",
            "dobs": [],
            "aliases": [],
            "countries": [],
            "addresses": [],
            "categories": [],
            "profile_notes": None,
            "deceased_date": None,
        },
    ]
    (data / "hits.jsonl").write_text(
        "\n".join(json.dumps(h) for h in hits) + "\n", encoding="utf-8"
    )
    for name in (
        "customers",
        "accounts",
        "onboarding",
        "kyc_checks",
        "notes",
        "search_results",
    ):
        (data / f"{name}.jsonl").write_text("", encoding="utf-8")
    (data / "name_variants.json").write_text(
        json.dumps({"groups": [], "company_legal_forms": []}), encoding="utf-8"
    )

    def boom(store: DataStore, hit_id: str):
        if hit_id == "H-AAAAAA":
            raise RuntimeError("boom")
        from namesake.schema import make_line

        hit = store.hits[hit_id]
        return make_line(
            hit_id,
            hit["alert_id"],
            "REVIEW",
            "INSUFFICIENT_DATA",
            None,
            "Ok.",
            [hit_id],
        )

    set_engine(boom)
    try:
        out = tmp_path / "out.jsonl"
        run_pipeline(str(data), str(out))
        rows = [json.loads(ln) for ln in out.read_text().splitlines() if ln.strip()]
        assert len(rows) == 2
        by_id = {r["hit_id"]: r for r in rows}
        assert by_id["H-AAAAAA"]["decision"] == "REVIEW"
        assert by_id["H-BBBBBB"]["decision"] == "REVIEW"
    finally:
        set_engine(None)


def test_system_has_no_third_party_imports() -> None:
    """SPEC §7: system/ uses the standard library only."""
    banned = {
        "requests",
        "httpx",
        "openai",
        "numpy",
        "pandas",
        "sklearn",
        "torch",
        "transformers",
        "pydantic",
        "orjson",
        "ujson",
        "yaml",
        "toml",
        "dateutil",
        "pytz",
        "bs4",
        "lxml",
        "regex",
    }
    found = []
    for path in (ROOT / "system").rglob("*"):
        if path.suffix not in {".py", ""} and path.name != "run":
            continue
        if path.is_dir():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name in banned:
            if f"import {name}" in text or f"from {name}" in text:
                found.append((str(path), name))
    assert found == []
