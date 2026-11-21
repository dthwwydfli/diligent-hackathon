"""CLI for system/run."""

from __future__ import annotations

import argparse
import os
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Namesake screening decisions")
    parser.add_argument("data_folder", help="folder with alerts.jsonl, hits.jsonl, …")
    parser.add_argument("output_file", help="path for one JSON line per hit")
    args = parser.parse_args(argv)

    data = os.path.abspath(args.data_folder)
    out = os.path.abspath(args.output_file)
    if not os.path.isdir(data):
        print(f"data folder not found: {data}", file=sys.stderr)
        return 2

    from namesake.pipeline import run_pipeline

    run_pipeline(data, out)
    return 0
