"""R2.2: sensitivity of the frequency--consequence comparison to the grouping level.

Repeats the MR07 rolling-origin protocol (run_revision_priority_backtest.py) with part numbers
instead of two-digit ATA chapters as decision units. The ATA run reproduces the reported summary
as a check. Part numbers are attached by row order, which build_revision_event_consequences.py
preserves; ATA chapter and parts value are asserted to match row by row.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from ramsc.decision_priority import consequence_priority
from ramsc.panel import filter_tracked_unscheduled_mechanical, repo_data_paths
from run_revision_priority_backtest import fractional_top_k

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis_outputs/revision'
WEIGHTS = (0., .25, .5, .75, 1.)


def load_events():
    events = pd.read_csv(OUT / 'event_consequences.csv', parse_dates=['removed', 'available'])
    raw = filter_tracked_unscheduled_mechanical(pd.read_excel(repo_data_paths(ROOT)['removals'])).reset_index(drop=True)
    assert len(raw) == len(events)
    assert ((pd.to_numeric(raw['ATA #']) // 100).astype(int).values == events.ata2.values).all()
    assert np.allclose(pd.to_numeric(raw['Std Cost'], errors='coerce').fillna(-1), events.parts_value.fillna(-1))
    events['part'] = raw['Part #'].astype(str).values
    return events


def evaluate(events, monthly, unit, k):
    rows, sizes = [], []
    for origin in pd.period_range('2024-12', '2025-12', freq='M'):
        hours = monthly.loc[monthly.period.le(origin)].groupby('pt_id').H_im.sum()
        eligible = hours.index[hours.ge(500)]
        past = events.loc[events.period.le(origin) & events.pt_id.isin(eligible)].copy()
        future = events.loc[events.period.gt(origin) & events.period.le(origin + 3) & events.pt_id.isin(eligible)].copy()
        past['work'] = past.labour_per_event.where(past.available.le(origin.end_time))
        future['work'] = future.labour_per_event.where(future.available.le((origin + 3).end_time))
        stats = past.groupby(unit).agg(n=('event_id', 'size'), labour_per_event=('work', 'mean'),
                                       parts_cost_per_event=('parts_value', 'mean'))
        stats['removal_rate'] = stats.n / hours.loc[eligible].sum()
        common = stats.dropna(subset=['labour_per_event', 'parts_cost_per_event']).copy()
        m_ref, c_ref = past.work.mean(), past.parts_value.mean()
        burdens = future.loc[future[unit].isin(common.index)].groupby(unit)[['work', 'parts_value']] \
            .sum(min_count=1).reindex(common.index).fillna(0)
        den = burdens.sum()
        sizes.append(dict(origin=str(origin), unit=unit, k=k, universe=len(common),
                          test_events_in_universe=int(future[unit].isin(common.index).sum()), test_events=len(future)))
        preds = {'frequency': common.removal_rate}
        for w in WEIGHTS:
            preds[f'w{w:.2f}'] = consequence_priority(common, labour_weight=w, labour_reference=m_ref, parts_reference=c_ref)
        for method, s in preds.items():
            cov = burdens.mul(fractional_top_k(s, k), axis=0).sum() / den
            rows.append(dict(origin=str(origin), unit=unit, k=k, method=method, work=cov.work, parts=cov.parts_value))
    return pd.DataFrame(rows), pd.DataFrame(sizes)


def run():
    panel = pd.read_csv(OUT / 'panel_aircraft_ata_month.csv')
    panel['period'] = pd.PeriodIndex(panel.month, freq='M')
    monthly = panel.drop_duplicates(['pt_id', 'month'])[['pt_id', 'period', 'H_im']]
    events = load_events()
    events['period'] = events.removed.dt.to_period('M')
    events = events.merge(monthly, on=['pt_id', 'period'], how='inner', validate='many_to_one')
    events = events.loc[events.H_im.gt(0)].copy()
    results, sizes = zip(*[evaluate(events, monthly, u, k) for u, k in (('ata2', 3), ('part', 5), ('part', 10))])
    res, size = pd.concat(results), pd.concat(sizes)
    base = res[res.method.eq('frequency')].set_index(['unit', 'k', 'origin'])
    out = []
    for (unit, k, method), g in res[res.method.ne('frequency')].groupby(['unit', 'k', 'method']):
        g = g.set_index(['unit', 'k', 'origin'])
        dw, dp = (g.work - base.work).dropna(), (g.parts - base.parts).dropna()
        out.append(dict(unit=unit, k=k, method=method, work_mean_pp=100 * dw.mean(), parts_mean_pp=100 * dp.mean(),
                        joint_wins=int((dw.gt(1e-12) & dp.gt(1e-12)).sum()),
                        joint_losses=int((dw.lt(-1e-12) & dp.lt(-1e-12)).sum()),
                        equal=int((dw.abs().lt(1e-12) & dp.abs().lt(1e-12)).sum()),
                        mixed=int(len(dw) - (dw.gt(1e-12) & dp.gt(1e-12)).sum() - (dw.lt(-1e-12) & dp.lt(-1e-12)).sum()
                                  - (dw.abs().lt(1e-12) & dp.abs().lt(1e-12)).sum())))
    summ = pd.DataFrame(out)
    freq = res[res.method.eq('frequency')].groupby(['unit', 'k'])[['work', 'parts']].mean().mul(100)
    summ.to_csv(OUT / 'granularity_priority_summary.csv', index=False)
    res.to_csv(OUT / 'granularity_priority_by_origin.csv', index=False)
    size.to_csv(OUT / 'granularity_universe.csv', index=False)
    print(summ.round(2).to_string(index=False))
    print(freq.round(2))
    print(size.groupby(['unit', 'k'])[['universe', 'test_events_in_universe', 'test_events']].agg(['min', 'max']))
    rng = size.groupby(['unit', 'k']).universe.agg(['min', 'max'])
    name = {'ata2': 'ATA chapter', 'part': 'Part number'}
    lines = [r'\begin{table}[htbp]', r'\centering', r'\small',
             r'\caption{Sensitivity of the priority comparison to the decision unit: mean coverage difference from frequency over 13 origins (percentage points) and origins in which the priority is better (B) or worse (W) on both outcomes.}',
             r'\label{tab:granularity}', r'\resizebox{\linewidth}{!}{%', r'\begin{tabular}{lrrlrrrr}', r'\toprule',
             r'Decision unit & $k$ & Universe & Priority & Work (pp) & Parts value (pp) & B & W \\', r'\midrule']
    for (unit, k), g in summ.groupby(['unit', 'k'], sort=False):
        f = freq.loc[(unit, k)]
        lines.append(f"{name[unit]} & {k} & {rng.loc[(unit, k), 'min']}--{rng.loc[(unit, k), 'max']} & Frequency (\\%) & {f.work:.1f} & {f.parts:.1f} & & \\\\")
        for r in g.itertuples():
            lines.append(f" & & & $w={float(r.method[1:]):.2f}$ & {r.work_mean_pp:+.1f} & {r.parts_mean_pp:+.1f} & {r.joint_wins} & {r.joint_losses} \\\\")
        lines.append(r'\addlinespace')
    lines[-1] = r'\bottomrule'
    lines += [r'\end{tabular}}', r'\par\smallskip',
              r'{\footnotesize Same origins, eligibility, training-only references and fractional top-$k$ selection as Table~\ref{tab:revised-priority-coverage}. The universe contains decision units with both consequences observed in training; at part level it covers only part of the test removals. Origins overlap and are not independent replications.}',
              r'\end{table}']
    (ROOT / 'latex/manuscript/tables/table_granularity.tex').write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    run()
