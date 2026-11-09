"""Sensitivity of fixed temporal priorities to unknown event-associated work."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from ramsc.missing_work import paired_coverage_bounds, unbounded_paired_coverage

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'analysis_outputs/revision'
inputs = pd.read_csv(OUT/'rolling_priority_inputs.csv')
cohorts = pd.read_csv(OUT/'rolling_priority_cohorts.csv').set_index('origin')
previous = pd.read_csv(OUT/'rolling_priority_summary.csv')
events = pd.read_csv(OUT/'event_consequences.csv',parse_dates=['removed','available'])
events['period'] = events.removed.dt.to_period('M')
panel = pd.read_csv(OUT/'panel_aircraft_ata_month.csv')
panel['period'] = pd.PeriodIndex(panel.month,freq='M')
monthly = panel.drop_duplicates(['pt_id','month'])[['pt_id','period','H_im']]
events = events.merge(monthly,on=['pt_id','period'],how='inner',validate='many_to_one')
events = events.loc[events.H_im.gt(0)].copy()
rows = []
unbounded_rows = []
for origin_text, group in inputs.groupby('origin'):
    origin = pd.Period(origin_text,freq='M')
    hours = monthly.loc[monthly.period.le(origin)].groupby('pt_id').H_im.sum()
    eligible = hours.index[hours.ge(500)]
    frequency = group.loc[group.method.eq('frequency')].set_index('ata2').selection
    universe = frequency.index
    future = events.loc[events.period.gt(origin)&events.period.le(origin+3)
                        &events.pt_id.isin(eligible)&events.ata2.isin(universe)].copy()
    future['observed'] = future.labour_per_event.where(future.available.le((origin+3).end_time))
    future['missing'] = future.observed.isna()
    # Partial values are used only as retrospective outcome floors, never ranking features.
    future['floor'] = future.known_allocated_work.fillna(0).where(future['missing'],0)
    observed = future.groupby('ata2')['observed'].sum().reindex(universe,fill_value=0)
    missing = future.groupby('ata2')['missing'].sum().reindex(universe,fill_value=0)
    floor = future.groupby('ata2')['floor'].sum().reindex(universe,fill_value=0)
    required_cap = future['floor'].max()
    scale = cohorts.loc[origin_text,'labour_reference']
    assert np.isclose(observed.sum(),cohorts.loc[origin_text,'common_test_work'])
    baseline = previous.loc[previous.origin.eq(origin_text)&previous.method.eq('frequency'),'work_coverage'].iloc[0]
    for method, subset in group.groupby('method'):
        if method=='frequency':
            continue
        delta = subset.set_index('ata2').selection.reindex(universe)-frequency
        point = float(np.dot(delta,observed)/observed.sum())
        old = previous.loc[previous.origin.eq(origin_text)&previous.method.eq(method),'work_coverage'].iloc[0]-baseline
        assert np.isclose(point,old,atol=1e-12)
        free_low, free_high = unbounded_paired_coverage(observed,missing,delta)
        partial_low, partial_high = unbounded_paired_coverage(observed+floor,missing,delta)
        unbounded_rows.append(dict(origin=origin_text,method=method,
                                   infimum=free_low,supremum=free_high,
                                   partial_floor_infimum=partial_low,
                                   partial_floor_supremum=partial_high,
                                   same_selection=bool(delta.eq(0).all()),
                                   positive_reversal_possible=bool(partial_high>1e-12)))
        for factor in (0.,.5,1.,2.,5.,10.):
            cap = factor*scale
            upper = missing*cap
            low,high = paired_coverage_bounds(observed,upper,delta)
            feasible = bool(cap+1e-9 >= required_cap)
            floor_low,floor_high = (paired_coverage_bounds(observed+floor,
                                      (upper-floor).clip(lower=0),delta) if feasible else (np.nan,np.nan))
            rows.append(dict(origin=origin_text,method=method,factor=factor,cap_hours=cap,
                             required_cap_hours=required_cap,compatible_with_partial=feasible,
                             observed_difference=point,lower=low,upper=high,
                             floor_lower=floor_low,floor_upper=floor_high,
                             missing_events=int(missing.sum()),known_partial_hours=float(floor.sum()),
                             observed_hours=float(observed.sum()),
                             same_selection=bool(delta.eq(0).all()),
                             positive_unbounded=bool(((delta>0)&(missing>0)).any()),
                             negative_unbounded=bool(((delta<0)&(missing>0)).any())))
result = pd.DataFrame(rows)
pd.DataFrame(unbounded_rows).to_csv(OUT/'missing_work_unbounded.csv',index=False)
pd.DataFrame(unbounded_rows).groupby('method').agg(
    equal_origins=('same_selection','sum'),
    positive_reversal_origins=('positive_reversal_possible','sum'),
    mean_floor_infimum=('partial_floor_infimum','mean'),
    mean_floor_supremum=('partial_floor_supremum','mean')
).to_csv(OUT/'missing_work_unbounded_summary.csv')
result.to_csv(OUT/'missing_work_bounds.csv',index=False)
summary = result.groupby(['method','factor']).agg(mean_lower=('lower','mean'),
    mean_upper=('upper','mean'), mean_floor_lower=('floor_lower','mean'),
    mean_floor_upper=('floor_upper','mean'), compatible_origins=('compatible_with_partial','sum'),
    reversal_possible=('upper',lambda x:int(x.gt(1e-10).sum())),
    equal_origins=('same_selection','sum'))
summary.to_csv(OUT/'missing_work_summary.csv')
manifest = dict(protocol='docs/MR07_MISSING_WORK_PROTOCOL.md',origins=13,
    comparisons=len(result),factors=[0,.5,1,2,5,10],
    selection='fixed at original observed-data rankings; no refitting or weight choice',
    bounds='deterministic conditional envelopes, not confidence intervals',
    target='eventual work of test removals; distinguishes original horizon-available observed work',
    mean_bounds='averaged originwise envelopes; not one coherent imputation across overlapping horizons')
(OUT/'missing_work_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(summary.to_string())
print('Cap compatibility by factor:',result.groupby('factor').compatible_with_partial.sum().to_dict())
