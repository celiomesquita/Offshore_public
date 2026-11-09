"""Exploratory common-universe priority comparisons under MR07_PRIORITY_PROTOCOL."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from ramsc.decision_priority import consequence_priority

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'analysis_outputs/revision'


def fractional_top_k(scores, k=3):
    """Share boundary ties rather than resolve them by ATA identifier."""
    valid = scores.dropna()
    if len(valid) <= k:
        return valid*0+1
    boundary = valid.nlargest(k).iloc[-1]
    selected = valid.gt(boundary).astype(float)
    ties = valid.eq(boundary)
    selected.loc[ties] = (k-selected.sum())/ties.sum()
    return selected


def run():
    panel = pd.read_csv(OUT/'panel_aircraft_ata_month.csv')
    panel['period'] = pd.PeriodIndex(panel.month, freq='M')
    events = pd.read_csv(OUT/'event_consequences.csv', parse_dates=['removed', 'available'])
    events['period'] = events.removed.dt.to_period('M')
    monthly = panel.drop_duplicates(['pt_id', 'month'])[['pt_id', 'period', 'H_im']]
    events = events.merge(monthly, on=['pt_id', 'period'], how='inner', validate='many_to_one')
    events = events.loc[events.H_im.gt(0)].copy()
    rows, inputs, cohorts = [], [], []
    for origin in pd.period_range('2024-12', '2025-12', freq='M'):
        hours = monthly.loc[monthly.period.le(origin)].groupby('pt_id').H_im.sum()
        eligible = hours.index[hours.ge(500)]
        past = events.loc[events.period.le(origin) & events.pt_id.isin(eligible)].copy()
        future = events.loc[events.period.gt(origin) & events.period.le(origin+3)
                            & events.pt_id.isin(eligible)].copy()
        past['work'] = past.labour_per_event.where(past.available.le(origin.end_time))
        future['work'] = future.labour_per_event.where(future.available.le((origin+3).end_time))
        stats = past.groupby('ata2').agg(n=('event_id', 'size'),
                                         labour_per_event=('work', 'mean'),
                                         parts_cost_per_event=('parts_value', 'mean'),
                                         observed_work=('work', 'count'),
                                         observed_cost=('parts_value', 'count'))
        stats['removal_rate'] = stats.n/hours.loc[eligible].sum()
        stats['qM'] = stats.observed_work/stats.n
        stats['qC'] = stats.observed_cost/stats.n
        common = stats.dropna(subset=['labour_per_event', 'parts_cost_per_event']).copy()
        labour_ref, parts_ref = past.work.mean(), past.parts_value.mean()
        assert labour_ref > 0 and parts_ref > 0
        predictions = {'frequency':common.removal_rate}
        for w in (0., .25, .5, .75, 1.):
            predictions[f'consequence_w{w:.2f}'] = consequence_priority(
                common, labour_weight=w, labour_reference=labour_ref, parts_reference=parts_ref)
        target = future.loc[future.ata2.isin(common.index)]
        burdens = target.groupby('ata2')[['work', 'parts_value']].sum(min_count=1)
        # No observed valid burden contributes nothing to a measured-total sum;
        # this does not impute the underlying event consequence as zero.
        burdens = burdens.reindex(common.index).fillna(0)
        denominators = burdens.sum()
        cohorts.append(dict(origin=str(origin), eligible_aircraft=len(eligible),
                            common_atas=len(common), training_events=len(past),
                            test_events=len(future), common_test_events=len(target),
                            train_qM=past.work.notna().mean(), test_qM=future.work.notna().mean(),
                            train_qC=past.parts_value.notna().mean(), test_qC=future.parts_value.notna().mean(),
                            common_test_qM=target.work.notna().mean(),
                            common_test_work=denominators.work,
                            common_test_parts_value=denominators.parts_value,
                            all_test_work=future.work.sum(min_count=1),
                            all_test_parts_value=future.parts_value.sum(min_count=1),
                            labour_reference=labour_ref, parts_reference=parts_ref))
        for method, scores in predictions.items():
            selection = fractional_top_k(scores)
            assert np.isclose(selection.sum(), min(3, len(common)))
            covered = burdens.mul(selection, axis=0).sum()
            rows.append(dict(origin=str(origin), method=method, common_atas=len(common),
                             effective_k=selection.sum(),
                             work_coverage=covered.work/denominators.work if denominators.work>0 else np.nan,
                             parts_value_coverage=covered.parts_value/denominators.parts_value
                             if denominators.parts_value>0 else np.nan))
            for ata in common.index:
                row = common.loc[ata].to_dict()
                row.update(origin=str(origin), ata2=int(ata), method=method,
                           priority=scores[ata], selection=selection[ata])
                inputs.append(row)
    result = pd.DataFrame(rows)
    result.to_csv(OUT/'rolling_priority_summary.csv', index=False)
    baseline = result.loc[result.method.eq('frequency')].set_index('origin')
    paired = []
    for method, group in result.groupby('method'):
        if method == 'frequency':
            continue
        group = group.set_index('origin')
        work = group.work_coverage-baseline.work_coverage
        value = group.parts_value_coverage-baseline.parts_value_coverage
        paired.append(dict(method=method, work_mean_pp=100*work.mean(),
                           cost_mean_pp=100*value.mean(), work_wins=int(work.gt(1e-12).sum()),
                           cost_wins=int(value.gt(1e-12).sum()),
                           joint_wins=int((work.gt(1e-12)&value.gt(1e-12)).sum()),
                           joint_losses=int((work.lt(-1e-12)&value.lt(-1e-12)).sum()),
                           equal=int((work.abs().lt(1e-12)&value.abs().lt(1e-12)).sum())))
    pd.DataFrame(paired).to_csv(OUT/'rolling_priority_paired_differences.csv', index=False)
    pd.DataFrame(inputs).to_csv(OUT/'rolling_priority_inputs.csv', index=False)
    pd.DataFrame(cohorts).to_csv(OUT/'rolling_priority_cohorts.csv', index=False)
    (OUT/'rolling_priority_manifest.json').write_text(json.dumps(dict(
        protocol='docs/MR07_PRIORITY_PROTOCOL.md', origins=13, horizon_months=3, top_k=3,
        inference='descriptive; overlapping origins; latest signoff is only an availability proxy',
        cost='standard parts value, not expenditure or savings',
        missingness='observed complete-work outcomes only; coverage reported, no missing-as-zero imputation',
        safety='not included', legacy_score='not evaluated because historical full-window aggregates leak future data'
    ), indent=2)+'\n')
    print(result.groupby('method')[['work_coverage', 'parts_value_coverage']].mean().to_string())
    print(pd.DataFrame(cohorts)[['common_atas', 'train_qM', 'test_qM']].agg(['min','max']).to_string())


if __name__ == '__main__':
    run()
