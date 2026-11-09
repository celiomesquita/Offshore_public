"""Scenario S-B under Poisson and negative-binomial pipeline demand with the corrected METRIC core.

Responds to R3.7 (NBD as METRIC foundation). Same base, parts, calendar and lead time as
run_revision_metric.py; no Ao or grounded cost is exported. Two NB dispersions: the
part-level weighted method-of-moments value (monthly part counts) and the fleet-panel value
(stress test). Immediate fill under NB is reported as P(X < s) of the pipeline marginal,
which is an assumption about the distribution seen by arriving demands (RV01-05).
"""
from pathlib import Path
import json

import pandas as pd

from ramsc.availability import (SENSITIVITY_MAX_STOCK_LEVEL, _make_base, load_parts,
                                panel_nb_alpha, part_level_demand_diagnostic)
from ramsc.metric import solve_metric

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis_outputs" / "revision"

base = _make_base()
parts = load_parts(ROOT)
dispersion, _ = part_level_demand_diagnostic(ROOT)
part_alpha = float((dispersion.alpha_mom * dispersion.monthly_failures).sum() / dispersion.monthly_failures.sum())
panel_alpha = float(panel_nb_alpha(ROOT))

rows, stocks = [], {}
for label, model, alpha in [("Poisson", "poisson", 0.0),
                            ("NB, part-level alpha", "negbin", part_alpha),
                            ("NB, fleet-panel alpha", "negbin", panel_alpha)]:
    solution = solve_metric(base, parts, budget=float("inf"), minimum_fill_rate=0.85,
                            constraint_priority="min_fr", use_cost_weighting=True,
                            demand_model=model, nb_alpha=alpha,
                            max_stock_level=SENSITIVITY_MAX_STOCK_LEVEL)
    exact = pd.DataFrame([vars(p) for p in solution.parts])
    assert abs(exact.ebo.sum() - solution.sum_ebo) < 1e-9 and exact.fill_rate.min() >= 0.85
    stocks[label] = exact.stock.tolist()
    rows.append({"demand_model": label, "alpha": alpha, "investment_usd": solution.total_cost,
                 "total_ebo": solution.sum_ebo, "minimum_immediate_fill_rate": exact.fill_rate.min(),
                 "total_units": int(exact.stock.sum())})

table = pd.DataFrame(rows)
table.to_csv(OUT / "metric_nb_sensitivity.csv", index=False)
(OUT / "metric_nb_sensitivity_manifest.json").write_text(json.dumps(
    {"scenario": "S-B, per-part immediate fill >= 0.85", "calendar_hours": 821 * 24, "lead_time_days": 35,
     "part_alpha_weighted_mom": part_alpha, "panel_alpha": panel_alpha,
     "max_stock_level": SENSITIVITY_MAX_STOCK_LEVEL, "ao_exported": False}, indent=2) + "\n", encoding="utf-8")
print(table.to_string(index=False))
