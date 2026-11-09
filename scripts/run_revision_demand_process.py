"""R3.3/R3.7: fleet-level demand process and removal intervals for the two leading METRIC parts.

METRIC assumes Poisson demand at the fleet level (Palm's theorem), i.e. exponential times between
successive demands for a part. This can be examined from removal dates without observing surviving
installations. Removal intervals (days on aircraft) are summarised descriptively only, because the
extract contains removed items and no right-censored survivors.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import lilliefors
from ramsc.availability import load_raw_datasets, filter_tracked_unscheduled_mechanical

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis_outputs/revision'
WINDOW = (pd.Timestamp('2024-01-01'), pd.Timestamp('2026-03-31'))

_, removals, _ = load_raw_datasets(ROOT)
mech = filter_tracked_unscheduled_mechanical(removals).copy()
mech['date'] = pd.to_datetime(mech['Removed Date_dt'], dayfirst=True, errors='coerce').dt.normalize()
mech['attached'] = pd.to_datetime(mech['Attached Date'], dayfirst=True, errors='coerce')
parts = pd.read_csv(ROOT / 'analysis_outputs/part_pareto_tracked_unscheduled.csv').head(20)['Part #'].astype(str)

rows = []
for rank, pn in enumerate(parts, 1):
    d = mech.loc[mech['Part #'].astype(str) == pn]
    days = d['date'].dropna().sort_values()
    per_day = days.value_counts()
    distinct = np.sort(per_day.index.values)
    gaps = np.diff(distinct).astype('timedelta64[D]').astype(float)
    weekly = days.dt.to_period('W').value_counts().reindex(
        pd.period_range(WINDOW[0], WINDOW[1], freq='W'), fill_value=0).to_numpy(float)
    row = dict(rank=rank, part=pn, removals=len(days), removal_days=len(distinct),
               share_multi_day=float((per_day > 1).sum() / len(per_day)),
               mean_batch=float(len(days) / len(distinct)),
               weekly_var_to_mean=float(weekly.var(ddof=1) / weekly.mean()))
    if len(gaps) >= 10:
        _, p_lf = lilliefors(gaps, dist='exp')
        shape, _, scale = stats.weibull_min.fit(gaps[gaps > 0], floc=0)
        row.update(gap_mean_days=float(gaps.mean()), gap_cv=float(gaps.std(ddof=1) / gaps.mean()),
                   lilliefors_exp_p=float(p_lf), gap_weibull_shape=float(shape))
    doa = pd.to_numeric(d['Days On A/c'], errors='coerce')
    row.update(doa_median=float(doa.median()), doa_q1=float(doa.quantile(.25)), doa_q3=float(doa.quantile(.75)),
               doa_zero=int((doa == 0).sum()), installed_before_window=int((d['attached'] < WINDOW[0]).sum()))
    for col in ('Purchase Count', 'Exchange Count', 'Repair Count', 'Exchg Repair Count', 'Scrap Count'):
        row[col.lower().replace(' ', '_') + '_nonzero'] = int(pd.to_numeric(d[col], errors='coerce').fillna(0).gt(0).sum())
    rows.append(row)

res = pd.DataFrame(rows)
res.to_csv(OUT / 'demand_process_top_parts.csv', index=False)
cost_cols = ['Purchase Count', 'Purchase Cost', 'Exchange Count', 'Exchange Cost', 'Repair Count', 'Repair Cost',
             'Exchg Repair Count', 'Exchg Repair Cost', 'Scrap Count', 'Scrap Cost']
fill = {c: int(pd.to_numeric(mech[c], errors='coerce').fillna(0).ne(0).sum()) for c in cost_cols}
json.dump(dict(window=[str(w.date()) for w in WINDOW], nonzero_cost_fields_all_1711=fill,
               test='Lilliefors exponential test on gaps between distinct removal days; same-day removals treated as one batch'),
          open(OUT / 'demand_process_manifest.json', 'w'), indent=2)
pd.set_option('display.width', 250)
print(res.round(3).to_string(index=False))
print(fill)

lines = [r'\begin{table}[htbp]', r'\centering', r'\scriptsize',
         r'\caption{Fleet-level demand process and removal intervals for the 20 METRIC parts.}',
         r'\label{tab:demand-process}', r'\resizebox{\linewidth}{!}{%', r'\begin{tabular}{rlrrrrrrrr}', r'\toprule',
         r' & & & Removal & Mean & Weekly & Gap & Exp.\ test & Gap & Days on aircraft \\',
         r'Rank & Part & Removals & days & batch & var/mean & CV & $p$ & shape & median (IQR) \\', r'\midrule']
for r in res.itertuples():
    lines.append(f'{r.rank} & {r.part} & {r.removals} & {r.removal_days} & {r.mean_batch:.2f} & {r.weekly_var_to_mean:.2f} & '
                 f'{r.gap_cv:.2f} & {r.lilliefors_exp_p:.3f} & {r.gap_weibull_shape:.2f} & '
                 f'{r.doa_median:.0f} ({r.doa_q1:.0f}--{r.doa_q3:.0f}) \\\\')
lines += [r'\bottomrule', r'\end{tabular}}', r'\par\smallskip',
          r'{\footnotesize Gaps are days between distinct removal days of the part across the fleet; same-day removals form one batch. The exponential test is a Lilliefors test with estimated rate; the shape is a Weibull fit to positive gaps (1 for a Poisson process). Days on aircraft describe removed items only: the extract contains no surviving installations and includes installations made before the window, so these intervals are not lifetime estimates.}',
          r'\end{table}']
(ROOT / 'latex/manuscript/tables/table_demand_process.tex').write_text('\n'.join(lines) + '\n', encoding='utf-8')
