"""Build analysis_outputs/doc_task_removal_link.csv: work-order documents linked to tracked unscheduled removals.

One row per removal source document with its removal count, task rows, recorded man-hours and
non-standard (NST) task count. Used by the maintainability table and part-level labour allocation.
"""
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ramsc.constants import NST_SYSTEM_PREFIX
from ramsc.panel import filter_tracked_unscheduled_mechanical, load_raw_datasets

_, removals, tasks = load_raw_datasets(ROOT)
tracked = filter_tracked_unscheduled_mechanical(removals).dropna(subset=['Source Doc #'])
tracked['Source Doc #'] = tracked['Source Doc #'].astype(str)
docs = tracked.groupby('Source Doc #').agg(removals=('Part #', 'size'), aircraft=('Aircraft #', 'first'),
                                           parts=('Part #', 'nunique'))
tasks = tasks.assign(doc=tasks['Execution Doc #'].astype(str),
                     hours=pd.to_numeric(tasks['Tot Man Hours'], errors='coerce'),
                     nst=tasks['Task #'].astype(str).str.startswith(NST_SYSTEM_PREFIX, na=False))
work = tasks.groupby('doc').agg(tasks=('doc', 'size'), manhours=('hours', 'sum'), nst_tasks=('nst', 'sum'))
link = docs.join(work, how='inner').rename_axis('Source Doc #').reset_index()
out = ROOT / 'analysis_outputs' / 'doc_task_removal_link.csv'
out.parent.mkdir(parents=True, exist_ok=True)
link.to_csv(out, index=False)
print(f'{len(link)} linked documents written to {out}')
