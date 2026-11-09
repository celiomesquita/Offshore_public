"""R4.1: Spearman dependence of the original pillars and of the revised frequency/consequence components by ATA chapter."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis_outputs/revision'
TAB = ROOT / 'latex/manuscript/tables'
pill = pd.read_csv(OUT / 'pillar_dependency_inputs.csv')
ev = pd.read_csv(OUT / 'event_consequences.csv')

pill['A_cov'] = pill['A_raw'].where(pill['modelled_parts'] > 0)  # uncovered chapters are missing, not zero
comp = ev.groupby('ata2').agg(c=('parts_value', 'mean'))
comp['m'] = ev[ev.complete].groupby('ata2')['labour_per_event'].mean()
df = pill.set_index('ata2').join(comp)
df['lam'] = df['R_raw']
df['m_known'] = df['manhours_per_removal']


def rho(a, b):
    x = df[[a, b]].dropna()
    r, p = spearmanr(x[a], x[b])
    return r, p, len(x)


panels = {
    'pillars': [('R_raw', 'M_raw'), ('R_raw', 'C_raw'), ('M_raw', 'C_raw'), ('R_raw', 'A_cov'),
                ('M_raw', 'A_cov'), ('C_raw', 'A_cov'), ('R_raw', 'S_raw')],
    'components': [('lam', 'm'), ('lam', 'm_known'), ('lam', 'c'), ('m', 'c'), ('m_known', 'c')],
}
rows = []
for panel, pairs in panels.items():
    for a, b in pairs:
        r, p, n = rho(a, b)
        rows.append(dict(panel=panel, x=a, y=b, spearman=r, p_value=p, n=n))
res = pd.DataFrame(rows)
res.to_csv(OUT / 'component_dependence.csv', index=False)
print(res.round(3).to_string(index=False))

lab = {'R_raw': 'R (removal rate)', 'M_raw': 'M (total labour)', 'C_raw': 'C (parts + assumed AOG)',
       'A_cov': 'A (zero-stock EBO)', 'S_raw': 'S (keyword score)', 'lam': r'$\lambda$ (removal rate)',
       'm': r'$m$ (labour per complete event)', 'm_known': 'Known labour per removal',
       'c': r'$c$ (parts value per removal)'}
lines = [r'\begin{table}[htbp]', r'\centering', r'\small',
         r'\caption{Spearman rank correlations across ATA chapters for the original pillar scores and for the components of the revised priority.}',
         r'\label{tab:component-dependence}', r'\begin{tabular}{llrr}', r'\toprule',
         r'Variable 1 & Variable 2 & $\rho_S$ & $n$ \\', r'\midrule',
         r'\multicolumn{4}{l}{\emph{Original pillar scores (withdrawn composite)}} \\']
for panel in panels:
    if panel == 'components':
        lines += [r'\midrule', r'\multicolumn{4}{l}{\emph{Revised components}} \\']
    for r in res[res.panel == panel].itertuples():
        lines.append(f'{lab[r.x]} & {lab[r.y]} & {r.spearman:.2f} & {r.n} \\\\')
lines += [r'\bottomrule', r'\end{tabular}', r'\par\smallskip',
          r'{\footnotesize Full 27-month window. A is evaluated only for the chapters containing modelled parts; uncovered chapters are missing, not zero. $m$ uses only removals with complete linked work and is undefined for chapters without such cases. Correlations describe association across chapters, not causal dependence.}',
          r'\end{table}']
(TAB / 'table_component_dependence.tex').write_text('\n'.join(lines) + '\n', encoding='utf-8')
json.dump({'inputs': ['pillar_dependency_inputs.csv', 'event_consequences.csv'],
           'output': 'component_dependence.csv'}, open(OUT / 'component_dependence_manifest.json', 'w'), indent=2)
