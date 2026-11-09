"""Reconstruct event-linked consequences without filling missing values with zero."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from ramsc.panel import filter_tracked_unscheduled_mechanical, repo_data_paths
from ramsc.anonymize import aircraft_id_lookup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'analysis_outputs/revision'


def allocate_document_work(events, tasks):
    """Allocate document work once; incomplete documents retain missing complete work."""
    docs = tasks.groupby('doc').agg(task_rows=('work', 'size'),
                                   observed_work=('work', 'count'),
                                   dated_tasks=('signed', 'count'),
                                   negative_work=('work', lambda x: int(x.lt(0).sum())),
                                   work_known=('work', lambda x: x.sum(min_count=1)),
                                   last_signed=('signed', 'max'))
    event_docs = events.groupby('doc').agg(event_count=('doc', 'size'),
                                         last_removal=('removed', 'max'))
    docs = event_docs.join(docs)
    docs['complete'] = (docs.task_rows.gt(0) & docs.observed_work.eq(docs.task_rows)
                        & docs.dated_tasks.eq(docs.task_rows) & docs.negative_work.eq(0)
                        & ~docs.index.to_series().str.startswith('ALHWO'))
    docs['available'] = docs[['last_removal', 'last_signed']].max(axis=1).where(docs.complete)
    docs['labour_per_event'] = (docs.work_known/docs.event_count).where(docs.complete)
    result = events.join(docs[['labour_per_event', 'available', 'complete', 'task_rows',
                               'observed_work', 'dated_tasks', 'work_known', 'event_count']], on='doc')
    result['known_allocated_work'] = result.work_known/result.event_count
    expected = docs.loc[docs.complete, 'work_known'].sum()
    assert np.isclose(result.labour_per_event.sum(), expected)
    return result, docs


def run():
    paths = repo_data_paths(ROOT)
    raw = pd.read_excel(paths['removals'])
    raw_tasks = pd.read_excel(paths['tasks'])
    removals = filter_tracked_unscheduled_mechanical(raw).copy()
    events = pd.DataFrame(dict(doc=removals['Source Doc #'].astype('string'),
                               removed=pd.to_datetime(removals['Removed Date'], dayfirst=True),
                               ata2=(pd.to_numeric(removals['ATA #'])//100).astype(int),
                               pt_id=removals['Aircraft #'].astype('string').map(aircraft_id_lookup()),
                               parts_value=pd.to_numeric(removals['Std Cost'], errors='coerce')))
    assert events.doc.notna().all()
    assert (events.parts_value.dropna() >= 0).all()
    tasks = pd.DataFrame(dict(doc=raw_tasks['Execution Doc #'].astype('string'),
                              work=pd.to_numeric(raw_tasks['Tot Man Hours'], errors='coerce'),
                              signed=pd.to_datetime(raw_tasks['Tech Sign Off Date'],
                                                    format='%m/%d/%Y', errors='coerce')))
    result, docs = allocate_document_work(events, tasks)
    result = result.reset_index(drop=True)
    result.insert(0, 'event_id', ['EV-%05d' % (i+1) for i in range(len(result))])
    result['document_id'] = ['DOC-%05d' % (i+1) for i in pd.factorize(result.doc, sort=True)[0]]
    result = result.drop(columns='doc')
    result.to_csv(OUT/'event_consequences.csv', index=False)
    coverage = result.groupby('ata2').agg(events=('event_id', 'size'),
                                         work_complete=('labour_per_event', 'count'),
                                         parts_value_complete=('parts_value', 'count'),
                                         work_complete_total=('labour_per_event', lambda x:x.sum(min_count=1)),
                                         parts_value_total=('parts_value', lambda x:x.sum(min_count=1)))
    coverage['qM'] = coverage.work_complete/coverage.events
    coverage['qC'] = coverage.parts_value_complete/coverage.events
    coverage.to_csv(OUT/'event_consequence_coverage.csv')
    manifest = dict(events=len(result), documents=len(docs),
                    documents_with_tasks=int(docs.task_rows.notna().sum()),
                    complete_documents=int(docs.complete.sum()),
                    complete_labour_events=int(result.labour_per_event.notna().sum()),
                    complete_zero_labour_documents=int((docs.complete & docs.work_known.eq(0)).sum()),
                    complete_work_total=float(result.labour_per_event.sum()),
                    known_linked_work_total=float(docs.work_known.sum()),
                    no_aircraft_events=int(result.pt_id.isna().sum()),
                    parts_value_total=float(result.parts_value.sum()),
                    negative_task_rows=int(tasks.work.lt(0).sum()),
                    scope='document-associated work; standard part value is not actual expenditure',
                    availability='latest signoff/removal proxy, not transaction-time history',
                    source_sha256={name:hashlib.sha256(path.read_bytes()).hexdigest()
                                   for name,path in paths.items() if name in ('tasks','removals')})
    (OUT/'event_consequence_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    run()
