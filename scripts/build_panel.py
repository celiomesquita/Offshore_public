#!/usr/bin/env python3
"""Build the aircraft × ATA × month RAMSC panel."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ramsc.panel import build_public_panel
from ramsc.anonymize import load_aircraft_id_map


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the anonymised aircraft × ATA × month panel (Step 1)."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "analysis_outputs" / "public" / "panel_aircraft_ata_month.csv",
        help="Destination CSV (anonymised publication export)",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=ROOT / "analysis_outputs" / "panel_build_summary.json",
        help="Optional JSON summary for internal inspection",
    )
    parser.add_argument(
        "--map",
        type=Path,
        default=None,
        help="Confidential aircraft ID map",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    panel, summary = build_public_panel(root=ROOT, map_path=args.map)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(args.output, index=False)

    summary_data = summary.as_dict()
    lookup = load_aircraft_id_map(args.map).set_index("actual_id")["public_id"].to_dict()
    summary_data["low_exposure_aircraft"] = [lookup[value] for value in summary.low_exposure_aircraft]
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")

    print(f"Wrote {len(panel):,} rows to {args.output}")
    print(json.dumps(summary_data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
