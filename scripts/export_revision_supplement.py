"""Generate the revised supplement from verified result files, without raw data."""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'analysis_outputs/revision'
DEST = ROOT/'supplementary/revision_tables.tex'
chunks = []

def table(caption, label, headers, rows, alignment):
    chunks.extend([r'\begin{small}', r'\setlength{\tabcolsep}{4pt}',
                   r'\begin{longtable}{' + alignment + '}',
                   r'\caption{' + caption + r'}\label{' + label + r'}\\',
                   r'\toprule', ' & '.join(headers) + r' \\', r'\midrule', r'\endfirsthead',
                   r'\toprule', ' & '.join(headers) + r' \\', r'\midrule', r'\endhead'])
    chunks.extend(' & '.join(map(str, row)) + r' \\' for row in rows)
    chunks.extend([r'\bottomrule', r'\end{longtable}', r'\end{small}'])

chunks.append(r'\section{Samples, units and observation limits}')
table('Sample and unit registry. Counts refer to distinct stated populations.', 'tab:s-samples',
      ['Population or quantity', 'Value / interpretation'], [
          ['Observation window', '1 January 2024--31 March 2026; 821 calendar days'],
          ['Flight records / fleet exposure', '11,926 records / 33,486.6 flight hours'],
          ['Populated removal records', '7,308; not the 32,767 physical worksheet rows'],
          ['Tracked unscheduled mechanical removals', '1,711; 43 lack an aircraft identifier'],
          ['Panel-linked removals', '1,668 before the model-specific exposure exclusions'],
          ['Full-window NB events', '1,499; distinct from rolling training/test samples'],
          ['Maintenance-task records', '57,029'],
          ['Removal-linked documents / with tasks', '1,263 / 1,207'],
          ['Complete linked-work documents / events', '354 / 376'],
          ['Complete / known linked work', '2,043.80 / 33,564.51 labour-hours; different completeness rules'],
          ['Recorded parts value', 'USD 56,313,204.83; not actual expenditure'],
          ['Removal installation intervals', 'Calendar days; no surviving installed population observed'],
          ['Empirical logistics time', 'Calendar hours; 19,704-hour window; assumed 35-day lead time'],
          ['Synthetic lifetime', 'Operating days; ageing pauses during downtime'],
      ], r'p{6cm}p{9cm}')
chunks.append('Work is allocated once per linked document, equally across its tracked removals. Complete work requires valid task hours and sign-off dates; unresolved zero-hour administrative orders are excluded. The latest removal/sign-off date is a retrospective information-availability proxy, not a transaction timestamp. Independent safety assessment and observed AOG intervals are unavailable. No pseudocensored survival sample is constructed.')
selection = pd.read_csv(OUT/'selection_by_ata.csv')
table('Work completeness by ATA chapter. Zero complete cases are retained.', 'tab:s-selection',
      ['ATA', 'Removals', 'Complete events', 'Complete (\\%)'],
      [[int(r.ata2), int(r.events), int(r.complete), f'{100*r.coverage:.2f}'] for r in selection.itertuples()], 'rrrr')

chunks.append(r'\section{Rolling forecasts and priority evaluation}')
counts = pd.read_csv(OUT/'rolling_count_summary.csv')
means = counts.groupby(['horizon','method']).agg(origins=('origin','nunique'),mae=('mae','mean'),rmse=('rmse','mean')).reset_index()
names = dict(cumulative_rate='Cumulative rate', recent_rate='Recent rate', poisson_trend='Poisson', nb2_trend='NB2')
table('Mean errors across rolling origins; these are descriptive point comparisons.', 'tab:s-forecasts',
      ['Horizon (months)', 'Method', 'Origins', 'MAE', 'RMSE'],
      [[int(r.horizon), names.get(r.method,r.method.replace('_',' ')), int(r.origins), f'{r.mae:.6f}', f'{r.rmse:.6f}'] for r in means.itertuples()], 'rlrrr')
chunks.append('Eligibility and estimation use only past observations; counts are conditioned on realised future flight hours. The 46 fitted count models converged. Overlapping origins are not independent replications, and no forecast-interval or significance claim is made.')
priority = pd.read_csv(OUT/'rolling_priority_summary.csv').groupby('method')[['work_coverage','parts_value_coverage']].mean()
table('Mean priority coverage over 13 three-month origins; top-three selection with fractional boundary ties.', 'tab:s-priorities',
      ['Method', 'Observed work (\\%)', 'Parts value (\\%)'],
      [[name.replace('consequence_w','Labour weight ').replace('frequency','Frequency'),f'{100*r.work_coverage:.4f}',f'{100*r.parts_value_coverage:.4f}'] for name,r in priority.iterrows()], 'lrr')
chunks.append('Each origin uses the same training-defined ATA universe across methods, containing 15--18 chapters with both consequences observed. Weights are prespecified preference scenarios. No weight is chosen by test performance; coverage does not measure realised operational savings.')

chunks.append(r'\section{Sensitivity to unobserved work}')
unbounded = pd.read_csv(OUT/'missing_work_unbounded_summary.csv')
table('Unbounded fixed-selection work envelopes, including known partial-work floors. Bounds are differences in coverage, not confidence limits.', 'tab:s-missing-work',
      ['$w$', 'Identical selections', 'Origins permitting positive reversal', 'Mean infimum', 'Mean supremum'],
      [[r.method.replace('consequence_w',''),int(r.equal_origins),int(r.positive_reversal_origins),f'{r.mean_floor_infimum:.6f}',f'{r.mean_floor_supremum:.6f}'] for r in unbounded.itertuples()], r'rp{2.4cm}p{3.6cm}rr')
chunks.append('The finite-cap grid uses 0, 0.5, 1, 2, 5 and 10 times the training mean complete work per event. All 390 method--origin--cap comparisons fail compatibility with known partial work and are not presented as plausible bounded imputations. The unbounded analysis contains 65 method--origin comparisons. It keeps the original selections fixed and changes the target to eventual work of test removals. Originwise envelopes ignore shared-document constraints and are not a coherent joint imputation across overlapping horizons. They do not account for refitting priorities.')

chunks.append(r'\section{Corrected logistics calculations}')
metric = pd.read_csv(OUT/'metric_corrected_scenarios.csv')
table('Poisson logistics scenarios with corrected EBO and immediate fill probability.', 'tab:s-logistics',
      ['Scenario', 'Investment (USD)', 'EBO', 'Minimum fill', 'Wait (h)'],
      [[r.scenario,f'{r.investment_usd:.2f}',f'{r.total_ebo:.6f}',f'{r.minimum_immediate_fill_rate:.6f}',f'{r.waiting_time_calendar_hours:.6f}'] for r in metric.itertuples()], 'lrrrr')
chunks.append('S-A and S-D impose investment budgets of USD 50,000 and USD 200,000. S-B and S-C impose minimum immediate fill probabilities of 0.85 and 0.95. The 20-part scope assumes quantity per aircraft equal to one and a common 35-day replenishment time. Waiting time is EBO divided by demand rate; it excludes intervention and administrative delays. No aircraft availability or grounded-cost estimate is derived from this ratio. Integer-reference EBO gaps are 0.088\\% and 0.726\\% for the budget scenarios. Separate enumeration of 60 three-part synthetic instances finds ten non-optimal heuristic allocations; this is not a bound on empirical fleet performance.')

chunks.append(r'\section{Synthetic joint-policy parameters and independent evaluation}')
parameters=json.loads((OUT/'joint_frozen_candidates.json').read_text())['parameters']
units = dict(assets='assets',shape='dimensionless',scale='operating days',lead_days='calendar days',corrective_days='calendar days',preventive_days='calendar days',part_price='USD/part',corrective_work_cost='USD/intervention',preventive_work_cost='USD/intervention',down_cost_per_day='USD/unavailable asset-day',capital_rate='fraction/year',warmup_days='calendar days',measurement_days='calendar days')
table('Base synthetic parameters. None are estimated component-lifetime or AOG parameters of the operator.', 'tab:s-joint-parameters',
      ['Parameter', 'Value', 'Unit'], [[key.replace('_',' '),value,units[key]] for key,value in parameters.items()], 'lrl')
chunks.append('The model has one essential position per asset, perfect renewal, unconstrained intervention teams, FIFO backlog and purchased replenishment after every demand. Events preserve on-hand stock plus pipeline minus backlog equal to base stock. Initial inventory investment is separate from annual cost. The selection grid has ten ages (60, 90, 120, 150, 180, 210, 240, 300, 360 and infinity) and 15 stock levels (0--12, 16, 24), with seeds 0--7. Candidates are frozen before 50 paired evaluation seeds 1000--1049. The selected joint policy is age 150 operating days with stock six; corrective stocking uses five. These policies do not have equal initial investment.')
contrast = pd.read_csv(OUT/'joint_independent_contrasts.csv').query("comparator == 'corrective_stock'")
table('Joint candidate minus corrective-stock policy: annual cost difference, with individual paired Monte Carlo 95\\% intervals.', 'tab:s-joint-evaluation',
      ['Setting', 'Difference (USD)', 'Lower', 'Upper', 'Relative (\\%)'],
      [[r.setting.replace('_',' '),f'{r.mean_difference:.2f}',f'{r.ci_low:.2f}',f'{r.ci_high:.2f}',f'{100*r.relative_mean_difference:.3f}'] for r in contrast.itertuples()], 'lrrrr')
chunks.append('Primary warm-up/measurement is 365/3,650 days. Checks use 0/3,650, 1,095/3,650 and 365/7,300 days. Intervals quantify simulation error with fixed inputs, not parameter uncertainty or external validity.')

chunks.append(r'\section{Synthetic transfer sensitivities}')
sensitivity = pd.read_csv(OUT/'joint_sensitivity_contrasts.csv')
table('Annual cost contrasts against the scenario-adapted corrective-stock policy. Adapted joint and unchanged base-candidate transfer are distinct comparisons.', 'tab:s-joint-sensitivity',
      ['Scenario', 'Policy', 'Difference (USD)', '95\\% lower', '95\\% upper', 'Relative (\\%)'],
      [[r.scenario.replace('_',' '),'Adapted' if r.policy=='joint_adapted' else 'Transferred',f'{r.mean_difference:.2f}',f'{r.ci_low:.2f}',f'{r.ci_high:.2f}',f'{100*r.relative_difference:.2f}'] for r in sensitivity.itertuples()], 'llrrrr')
chunks.append('The twelve scenarios vary one factor at a time: base; Weibull shape 0.7, 1 and 3 with mean lifetime preserved; purchase lead time 0, 5 and 60 days; downtime cost USD 0, 200 and 20,000 per unavailable asset-day; and part price USD 100 and 10,000. Selection uses seeds 0--7, followed by 50 new paired seeds 2000--2049. All scenario candidates are frozen before evaluation. Intervals are individual, without simultaneous multiple-comparison coverage. Adapted policies revert to corrective-only under shapes 0.7 and 1 and high part price. Small cost gains with zero downtime tariff accompany lower availability; the USD 200/day contrast includes zero. No repairable-item workshop, random lead time or interaction between sensitivity factors is represented.')
chunks.append(r'\section{Reproduction and anonymisation}')
chunks.append('The author authorises sharing of operational data after removal of company names, aircraft registrations and other identifying information. Reidentification mappings and identifiable originals are excluded. Anonymisation must preserve dates, exposure, event linkage and missingness needed to reproduce the stated analyses. The current local computational candidate reproduces the synthetic experiments and mathematical tests; this does not establish that the complete revised empirical package is already publicly accessible. Its data release requires verification of the anonymised inputs and their derived results. No superseded safety weighting, pseudocensoring, empirical AOG cost or 81-day replacement prescription is part of this supplement.')
DEST.write_text('\n\n'.join(chunks)+'\n',encoding='utf-8')
print('Generated revision_tables.tex from verified CSV/JSON sources.')
