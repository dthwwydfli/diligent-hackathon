"""Issue 11: each mutation flips in the expected direction. Labels from checker only."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.twin.operators import all_operators, label_with_checker  # noqa: E402


def test_every_operator_moves_expected_direction() -> None:
    """SPEC 7.1 / AC8: expected direction written from the policy branch first."""
    for case in all_operators():
        label = label_with_checker(case)
        decision = label["decision"]
        direction = case.expected_direction
        if direction == "to_DIFFERENT_ENTITY":
            assert decision == "DIFFERENT_ENTITY", case.op
        elif direction == "to_SAME_ENTITY":
            assert decision == "SAME_ENTITY", case.op
        elif direction == "to_REVIEW":
            assert decision == "REVIEW", case.op
        else:
            raise AssertionError(f"unknown direction {direction}")


def test_twin_labels_come_from_checker_not_engine() -> None:
    """Twin labels must not import the engine."""
    import inspect

    import tools.twin.operators as op

    src = inspect.getsource(op.label_with_checker)
    assert "namesake" not in src
    assert "checker" in src
