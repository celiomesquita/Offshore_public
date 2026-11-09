"""Regenerate verified logistics outputs without exporting unvalidated Ao."""
from pathlib import Path
import json
import pandas as pd
from ramsc.availability import _make_base, load_parts, run_scenarios, part_detail_table

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / 'analysis_outputs' / 'revision'
out.mkdir(parents=True, exist_ok=True)
base = _make_base()
parts = load_parts(ROOT)
solutions = run_scenarios(base, parts, {'S-A':50000, 'S-D':200000}, {'S-B':.85, 'S-C':.95})
rows = []
for label, solution in solutions.items():
    exact = pd.DataFrame([vars(part) for part in solution.parts])
    exact.to_csv(out / f'metric_{label.lower()}_exact.csv', index=False)
    assert abs(exact.ebo.sum() - solution.sum_ebo) < 1e-9
    if label in ('S-A','S-D'):
        assert solution.total_cost <= {'S-A':50000,'S-D':200000}[label]
    else:
        assert exact.fill_rate.min() >= {'S-B':.85,'S-C':.95}[label]
    rows.append({'scenario':label, 'investment_usd':solution.total_cost,
                 'total_ebo':solution.sum_ebo, 'minimum_immediate_fill_rate':exact.fill_rate.min(),
                 'waiting_time_calendar_hours':solution.waiting_time_hours})
comparison = pd.DataFrame(rows).sort_values('scenario')
comparison.to_csv(out / 'metric_corrected_scenarios.csv', index=False)
manifest = {'study_start':'2024-01-01','study_end_exclusive':'2026-04-01',
            'calendar_hours':821*24,'fleet_flight_hours':33486.6,'aircraft':24,
            'duty_cycle':base.duty_cycle,'lead_time_days':35,
            'part_source':'analysis_outputs/part_pareto_tracked_unscheduled.csv',
            'parts':len(parts),'qpa':1,
            'availability':'legacy Ao deliberately omitted pending reformulation',
            'cost':'legacy grounded_cost omitted pending dimensional reconciliation'}
(out/'metric_corrected_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(comparison.to_string(index=False))
