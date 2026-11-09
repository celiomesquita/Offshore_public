"""Describe selection into complete linked-work records; no missing-at-random claim."""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'analysis_outputs/revision'
events = pd.read_csv(OUT/'event_consequences.csv', parse_dates=['removed','available'])
events['selected'] = events.labour_per_event.notna()
events['month'] = events.removed.dt.to_period('M').astype(str)
ata = events.groupby('ata2').agg(events=('event_id','size'), complete=('selected','sum'),
                                standard_parts_value=('parts_value','sum'))
ata['coverage'] = ata.complete/ata.events
ata['all_share'] = ata.events/ata.events.sum()
ata['complete_share'] = ata.complete/ata.complete.sum()
ata['share_difference_pp'] = 100*(ata.complete_share-ata.all_share)
ata.to_csv(OUT/'selection_by_ata.csv')
monthly = events.groupby('month').agg(events=('event_id','size'), complete=('selected','sum'))
monthly['coverage'] = monthly.complete/monthly.events
monthly.to_csv(OUT/'selection_by_month.csv')
lag = (events.available-events.removed).dt.total_seconds()/86400
manifest = dict(events=len(events), complete=int(events.selected.sum()),
                overall_coverage=float(events.selected.mean()),
                ata_distribution_total_variation=float((ata.all_share-ata.complete_share).abs().sum()/2),
                zero_coverage_atas=[int(a) for a in ata.index[ata.complete.eq(0)]],
                month_min_coverage=float(monthly.coverage.min()),
                month_max_coverage=float(monthly.coverage.max()),
                complete_availability_lag_median_days=float(lag.median()),
                complete_availability_lag_p90_days=float(lag.quantile(.9)),
                interpretation='descriptive selection; does not identify missing-data mechanism or permit correction')
(OUT/'selection_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
print(ata.sort_values('events',ascending=False).head(8).to_string())

summary = pd.read_csv(OUT/'rolling_priority_summary.csv').groupby('method')[
    ['work_coverage','parts_value_coverage']].mean()
labels = {'frequency':'Removal frequency', 'consequence_w0.00':'Parts value only ($w=0$)',
          'consequence_w0.25':'Combined ($w=0.25$)', 'consequence_w0.50':'Combined ($w=0.50$)',
          'consequence_w0.75':'Combined ($w=0.75$)', 'consequence_w1.00':'Labour only ($w=1$)'}
lines = [r'\begin{table}[htbp]',r'\centering',
         r'\caption{Exploratory three-month priority coverage, averaged across 13 rolling origins.}',
         r'\label{tab:revised-priority-coverage}',r'\setlength{\tabcolsep}{5pt}',r'\begin{tabular}{lrr}',r'\toprule',
         r'Priority & Observed work (\%) & Standard parts value (\%) \\',r'\midrule']
for method,label in labels.items():
    row=summary.loc[method]
    lines.append(f'{label} & {100*row.work_coverage:.2f} & {100*row.parts_value_coverage:.2f} '+r'\\')
lines += [r'\bottomrule',r'\end{tabular}',r'\par\smallskip',
          r'{\footnotesize Each method selects three ATA chapters from the same training-defined universe (15--18 chapters per origin). Denominators include only observed consequences in that universe. The labour weight $w$ is a scenario preference, not an elicited value. Overlapping origins are not independent replications; coverage is not realised savings.}',r'\end{table}']
(ROOT/'latex/manuscript/tables/table_revised_priority_coverage.tex').write_text('\n'.join(lines)+'\n')
