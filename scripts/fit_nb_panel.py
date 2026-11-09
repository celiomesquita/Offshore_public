#!/usr/bin/env python3
"""Fit the NB panel model and export Results Table R-3."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ramsc.reliability_nb import export_nb_panel_results


def main() -> int:
    estimates, summary, seasonality = export_nb_panel_results(ROOT)
    print("Exported Results Table R-3 and seasonality figure.")
    print(estimates.to_string(index=False))
    print(json.dumps(summary.__dict__, indent=2))
    peak = seasonality.loc[seasonality["irr"].idxmax()]
    trough = seasonality.loc[seasonality["irr"].idxmin()]
    print(f"Peak month IRR: {peak['month']} = {peak['irr']:.2f}")
    print(f"Trough month IRR: {trough['month']} = {trough['irr']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
