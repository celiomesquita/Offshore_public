"""Build analysis_outputs/part_pareto_tracked_unscheduled.csv: part-level Pareto of tracked unscheduled removals.

Input to the METRIC part selection (top 20) and to the demand-process diagnostics.
"""
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ramsc.panel import filter_tracked_unscheduled_mechanical, load_raw_datasets

hours, removals, _ = load_raw_datasets(ROOT)
fleet_hours = pd.to_numeric(hours['Hours'], errors='coerce').sum()
tracked = filter_tracked_unscheduled_mechanical(removals)
tracked = tracked.assign(days=pd.to_numeric(tracked['Days On A/c'], errors='coerce'),
                         cost=pd.to_numeric(tracked['Std Cost'], errors='coerce'))
# Order as groupby(...).size().sort_values(ascending=False), which fixes the tie order used for the top-20 selection.
order = tracked.groupby('Part #').size().sort_values(ascending=False).index
p = tracked.groupby('Part #').agg(**{'Part Description': ('Part Description', 'first')},
                                              removals=('Part #', 'size'), aircraft=('Aircraft #', 'nunique'),
                                              avg_days=('days', 'mean'), med_days=('days', 'median'),
                                              std_cost=('cost', 'sum')).reset_index()
p['rate_1000h'] = 1000 * p.removals / fleet_hours
p['mtbur_fleet_h'] = fleet_hours / p.removals
p = p.set_index('Part #').loc[order].reset_index()
p['share_pct'] = 100 * p.removals / p.removals.sum()
p['cum_share_pct'] = p.share_pct.cumsum()
out = ROOT / 'analysis_outputs' / 'part_pareto_tracked_unscheduled.csv'
p.to_csv(out, index=False)
print(f'{len(p)} parts; fleet hours {fleet_hours:,.1f}; written to {out}')
