"""Generate the manuscript sensitivity table from verified scenario outputs."""
from pathlib import Path
import json
import pandas as pd

root=Path(__file__).resolve().parents[1]
out=root/'analysis_outputs/revision'
manifest=json.loads((out/'joint_sensitivity_frozen.json').read_text())
contrasts=pd.read_csv(out/'joint_sensitivity_contrasts.csv').set_index(['scenario','policy'])
labels={'base':'Base','shape_0.7':'Weibull shape 0.7','shape_1':'Weibull shape 1',
        'shape_3':'Weibull shape 3','lead_0':'Lead time 0 days','lead_5':'Lead time 5 days',
        'lead_60':'Lead time 60 days','downcost_0':'Downtime USD 0/day',
        'downcost_200':'Downtime USD 200/day','downcost_20000':'Downtime USD 20,000/day',
        'price_100':'Part price USD 100','price_10000':'Part price USD 10,000'}
lines=[r'\begin{table}[htbp]',r'\centering',r'\small',
       r'\caption{Synthetic sensitivity: annual cost differences relative to scenario-adapted corrective stocking.}',
       r'\label{tab:joint-sensitivity}',r'\begin{tabular}{lrrrr}',r'\toprule',
       r'Scenario & $T$ (days) & $s$ & Adapted (\%) & Transferred (\%) \\',r'\midrule']
for key,label in labels.items():
    policy=manifest['scenarios'][key]['policies']['joint_adapted']
    age=r'$\infty$' if policy['age_days']=='infinity' else f'{policy["age_days"]:.0f}'
    adapted=100*contrasts.loc[(key,'joint_adapted'),'relative_difference']
    transferred=100*contrasts.loc[(key,'base_transferred'),'relative_difference']
    lines.append(f'{label} & {age} & {policy["stock"]} & {adapted:.2f} & {transferred:.2f} '+r'\\')
lines += [r'\bottomrule',r'\end{tabular}',r'\par\smallskip',
          r'{\footnotesize Negative values favour the compared policy. Transferred policy: $T=150$, $s=6$. Age is measured in operating days. Weibull-shape changes preserve mean life. All parameters are synthetic; mean differences use 50 new paired seeds. Zero differences indicate identical policies.}',r'\end{table}']
(root/'latex/manuscript/tables/table_joint_sensitivity.tex').write_text('\n'.join(lines)+'\n')
