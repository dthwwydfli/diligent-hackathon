"""Load packaged JSON data next to this package. One home per table."""

from __future__ import annotations

import json
import os
from functools import cache
from typing import Any, Dict


def _data_dir() -> str:
    return os.path.join(os.path.dirname(__file__), "data")


@cache
def load_json(name: str) -> Dict[str, Any]:
    path = os.path.join(_data_dir(), name)
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)
