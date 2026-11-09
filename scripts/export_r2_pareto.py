#!/usr/bin/env python3
"""Export Results Table R-2 (component Pareto with COUR)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ramsc.results_reliability import export_component_pareto


def main() -> int:
    table = export_component_pareto(ROOT)
    cols = [
        "Part #",
        "description_short",
        "removals",
        "rate_1000h",
        "parts_cost",
        "cour",
        "vol_rank",
        "cour_rank",
        "rank_diff",
    ]
    print(f"Exported top {len(table)} components for Results Table R-2.")
    print(table[cols].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
