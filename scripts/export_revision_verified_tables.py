"""Export only verified revision outputs for the reconciled manuscript."""
from pathlib import Path
import pandas as pd

root=Path(__file__).resolve().parents[1]
out=root/'analysis_outputs/revision'
tables=root/'latex/manuscript/tables'


def write(name, caption, label, header, rows, columns, note):
    lines=[r'\begin{table}[htbp]',r'\centering',r'\small',
           r'\caption{'+caption+'}',r'\label{'+label+'}',
           r'\begin{tabular}{'+columns+'}',r'\toprule',header+r' \\',r'\midrule']
    lines += [' & '.join(row)+r' \\' for row in rows]
    lines += [r'\bottomrule',r'\end{tabular}',r'\par\smallskip',
              r'{\footnotesize '+note+'}',r'\end{table}']
    (tables/name).write_text('\n'.join(lines)+'\n')


frame=pd.read_csv(out/'metric_corrected_scenarios.csv')
write('table_a2_metric_scenarios.tex','Corrected Poisson base-stock scenarios.',
      'tab:a2-metric-scenarios',r'Scenario & Investment (USD) & Total EBO & Min. fill & Wait (h)',
      [[r.scenario,f'{r.investment_usd:,.2f}',f'{r.total_ebo:.6f}',
        f'{r.minimum_immediate_fill_rate:.4f}',f'{r.waiting_time_calendar_hours:.2f}']
       for r in frame.itertuples()], 'lrrrr',
      r'S-A/S-D: greedy allocation under USD 50,000/200,000 budgets; S-B/S-C: per-part service targets 85/95\%. Waiting time is demand-weighted logistics delay in calendar hours, not aircraft downtime. Calendar calibration: 821 days; assumed lead time: 35 days.')
frame=pd.read_csv(out/'metric_s-b_exact.csv')
write('table_a1_metric_parts.tex','Corrected per-part outputs for Scenario S-B.',
      'tab:a1-metric-parts',r'Part identifier & Stock & Pipeline & EBO & Fill',
      [[str(r.name).split(' ')[0],str(r.stock),f'{r.pipeline:.4f}',f'{r.ebo:.6f}',f'{r.fill_rate:.4f}']
       for r in frame.itertuples()],'lrrrr',
      r'Model-conditional base-stock levels under the 85\% immediate-fill constraint. These are not operator-approved stock recommendations; repair capacity and replenishment histories are not observed.')
frame=pd.read_csv(out/'rolling_count_summary.csv').groupby(['horizon','method'])[['mae','rmse','bias_total']].mean()
names={'cumulative_rate':'Cumulative rate','recent_6m_rate':'Recent six-month rate',
       'poisson_trend':'Poisson trend','nb2_trend':'NB2 trend'}
write('table_revision_count_forecasts.tex','Retrospective rolling count forecasts conditional on realised exposure.',
      'tab:rolling-counts',r'Horizon & Method & MAE & RMSE & Total bias',
      [[str(h),names[m],f'{r.mae:.3f}',f'{r.rmse:.3f}',f'{r.bias_total:.3f}']
       for (h,m),r in frame.iterrows()],'llrrr',
      'Horizon in months; 13 origins at three months and ten at six months. Metrics are averaged over origins; positive bias denotes overprediction. Overlapping origins are not independent replications.')
coverage=pd.read_csv(out/'event_consequence_coverage.csv').sort_values('events',ascending=False)
write('table_revision_event_coverage.tex','Event counts, complete linked work and standard parts value by ATA.',
      'tab:event-coverage',r'ATA & Events & Complete work & Coverage (\%) & Parts value (USD)',
      [[str(int(r.ata2)),str(int(r.events)),str(int(r.work_complete)),f'{100*r.qM:.2f}',f'{r.parts_value_total:,.0f}']
       for r in coverage.head(10).itertuples()],'lrrrr',
      'Ten highest-volume chapters. Complete work requires linked hours and sign-off dates under the stated protocol. Standard parts value is not realised expenditure; missing work is not zero.')
