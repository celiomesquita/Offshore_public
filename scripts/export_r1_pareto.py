#!/usr/bin/env python3
"""Export Results Table R-1 and Figure R-P (ATA Pareto)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ramsc.results_reliability import export_reliability_pareto


def main() -> int:
    table = export_reliability_pareto(ROOT)
    print(f"Exported top {len(table)} ATA systems for Results Table R-1 and Figure R-P.")
    print(table[["ata2", "ata_label", "removals", "rate_1000h", "cum_share_pct"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
