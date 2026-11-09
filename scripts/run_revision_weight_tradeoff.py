"""R1.2/R2.3: weight as a labour--parts exchange rate, and selection changes relative to frequency.

The weight w in P = lambda [w m/m_ref + (1-w) c/c_ref] implies that one person-hour of conditional
labour is valued as r = w c_ref / ((1-w) m_ref) USD of standard parts value. Conversely, an
operator-specified rate r implies w = r m_ref / (r m_ref + c_ref). This script reports the implied
rates for the prespecified grid and evaluates rate-implied weights with the protocol of
run_revision_priority_backtest.py (same origins, eligibility, references and top-3 selection).
"""
from pathlib import Path
import numpy as np
import pandas as pd
from ramsc.decision_priority import consequence_priority
from run_revision_priority_backtest import fractional_top_k

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis_outputs/revision'
GRID = (0., .25, .5, .75, 1.)
RATES = (50., 100., 200., 500., 1000.)  # USD per person-hour, illustrative operator inputs


def run():
    panel = pd.read_csv(OUT / 'panel_aircraft_ata_month.csv')
    panel['period'] = pd.PeriodIndex(panel.month, freq='M')
    events = pd.read_csv(OUT / 'event_consequences.csv', parse_dates=['removed', 'available'])
    events['period'] = events.removed.dt.to_period('M')
    monthly = panel.drop_duplicates(['pt_id', 'month'])[['pt_id', 'period', 'H_im']]
    events = events.merge(monthly, on=['pt_id', 'period'], how='inner', validate='many_to_one')
    events = events.loc[events.H_im.gt(0)].copy()
    rows = []
    for origin in pd.period_range('2024-12', '2025-12', freq='M'):
        hours = monthly.loc[monthly.period.le(origin)].groupby('pt_id').H_im.sum()
        eligible = hours.index[hours.ge(500)]
        past = events.loc[events.period.le(origin) & events.pt_id.isin(eligible)].copy()
        future = events.loc[events.period.gt(origin) & events.period.le(origin + 3)
                            & events.pt_id.isin(eligible)].copy()
        past['work'] = past.labour_per_event.where(past.available.le(origin.end_time))
        future['work'] = future.labour_per_event.where(future.available.le((origin + 3).end_time))
        stats = past.groupby('ata2').agg(n=('event_id', 'size'), labour_per_event=('work', 'mean'),
                                         parts_cost_per_event=('parts_value', 'mean'))
        stats['removal_rate'] = stats.n / hours.loc[eligible].sum()
        common = stats.dropna(subset=['labour_per_event', 'parts_cost_per_event']).copy()
        m_ref, c_ref = past.work.mean(), past.parts_value.mean()
        burdens = future.loc[future.ata2.isin(common.index)].groupby('ata2')[['work', 'parts_value']] \
            .sum(min_count=1).reindex(common.index).fillna(0)
        den = burdens.sum()
        freq_sel = fractional_top_k(common.removal_rate)
        freq_cov = burdens.mul(freq_sel, axis=0).sum() / den
        specs = [('grid', w, w * c_ref / ((1 - w) * m_ref) if w < 1 else np.inf) for w in GRID]
        specs += [('rate', r * m_ref / (r * m_ref + c_ref), r) for r in RATES]
        for kind, w, rate in specs:
            sel = fractional_top_k(consequence_priority(common, labour_weight=w,
                                                        labour_reference=m_ref, parts_reference=c_ref))
            cov = burdens.mul(sel, axis=0).sum() / den
            rows.append(dict(origin=str(origin), kind=kind, weight=w, usd_per_hour=rate,
                             m_ref=m_ref, c_ref=c_ref,
                             selection_changed=bool(np.abs(sel - freq_sel).max() > 1e-12),
                             work_diff_pp=100 * (cov.work - freq_cov.work),
                             parts_diff_pp=100 * (cov.parts_value - freq_cov.parts_value)))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / 'weight_tradeoff_by_origin.csv', index=False)
    key = np.where(df.kind.eq('grid'), 'w=' + df.weight.round(2).astype(str),
                   'r=' + df.usd_per_hour.replace(np.inf, 0).round().astype(int).astype(str))
    summ = df.assign(spec=key).groupby('spec', sort=False).agg(
        weight_min=('weight', 'min'), weight_max=('weight', 'max'),
        rate_min=('usd_per_hour', 'min'), rate_max=('usd_per_hour', 'max'),
        origins_changed=('selection_changed', 'sum'),
        work_diff_pp=('work_diff_pp', 'mean'), parts_diff_pp=('parts_diff_pp', 'mean'))
    summ.to_csv(OUT / 'weight_tradeoff_summary.csv')
    print(summ.round(4).to_string())
    print('m_ref range', df.m_ref.min(), df.m_ref.max(), 'c_ref range', df.c_ref.min(), df.c_ref.max())


if __name__ == '__main__':
    run()
