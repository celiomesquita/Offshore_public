# Offshore helicopter maintenance records: data and code for reproducibility

Replication package for the revised manuscript

> A. C. P. de Mesquita, *From Offshore Maintenance Records to Fleet Priorities: Evidence Limits and Joint Policies*, submitted to *Reliability Engineering & System Safety* (manuscript JRESS-D-26-04044, revision).

It contains the anonymised operational data, the code needed to reproduce every analysis of the revised manuscript, and the supplementary material (Tables S1–S9).

## Contents

| Path | Content |
|---|---|
| `data/` | Anonymised operator extracts: `hours_flown.xlsx` (flight logs), `removals.xlsx` (component removals), `OMTH_tasks.xlsx` (work-order tasks) |
| `config/public/aircraft_id_map.csv` | Pseudonymised aircraft identifiers with total flight hours and exposure band |
| `analysis_outputs/revision/pillar_dependency_inputs.csv` | Original pillar scores by ATA chapter from the composite of the original submission (withdrawn in the revision); frozen input to the correlation table |
| `ramsc/` | Python package: panel construction, METRIC with corrected expected backorders, frequency–consequence priority, missing-work bounds, joint age–stock simulator |
| `scripts/` | One script per analysis; `scripts/run_all.py` runs the whole pipeline in order |
| `supplementary/` | Supplementary material: `supplementary.pdf` (Tables S1–S9) and LaTeX sources |

## Reproducing the results

Tested with Python 3.14; package versions are pinned in `requirements.txt`.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt     # Windows: .venv\Scripts\pip
python scripts/run_all.py                     # full pipeline, about 4 minutes
python scripts/run_all.py --skip-simulation   # empirical analyses only
```

The pipeline writes the results to `analysis_outputs/`, the tables and figures to `latex/manuscript/tables` and `latex/manuscript/figures`, and Supplementary Tables S1–S9 to `supplementary/revision_tables.tex`. Each script can also be run individually from the repository root with `PYTHONPATH=.:scripts` (Windows: `.;scripts`).

Run on the anonymised data, the pipeline reproduces exactly the results obtained from the original confidential records. Removal-count ties in the descriptive ATA and component Pareto tables may be listed in a different order than in the manuscript, and some generated tables were edited for layout in the manuscript; the CSV files are the reference values.

## Map from manuscript to scripts

| Manuscript element | Script |
|---|---|
| Panel, event dataset, work completeness | `build_panel.py`, `build_revision_event_consequences.py`, `build_doc_task_link.py`, `audit_revision_selection.py` |
| Pareto concentration, NB panel, maintainability table | `build_part_pareto.py`, `export_r1_pareto.py`, `export_r2_pareto.py`, `fit_nb_panel.py`, `export_m1_maintainability.py` |
| Rolling-origin count forecasts | `run_revision_count_forecasts.py`, `run_revision_rolling_baselines.py` |
| Frequency–consequence priority comparison | `run_revision_priority_backtest.py` |
| Weights as exchange rates | `run_revision_weight_tradeoff.py` |
| Correlation of pillars and components | `run_revision_component_dependence.py` |
| METRIC scenarios, integer benchmark, NB sensitivity | `run_revision_metric.py`, `run_revision_exact_stock.py`, `audit_revision_stock_optimality.py`, `run_revision_metric_nb.py` |
| Demand process of the METRIC parts | `run_revision_demand_process.py` |
| Missing-work bounds | `run_revision_missing_work.py` |
| Decision-unit sensitivity (ATA chapter vs part number) | `run_revision_granularity.py` |
| Known-truth synthetic fleets | `run_revision_priority_generator.py` |
| Joint age–stock policy and its sensitivity | `run_revision_joint_pilot.py`, `run_revision_joint_expanded.py`, `run_revision_joint_sensitivity.py` |
| Figures and supplementary tables | `export_revision_framework.py`, `export_revision_decision_figures.py`, `export_joint_sensitivity.py`, `export_revision_verified_tables.py`, `export_revision_supplement.py` |

## Data and anonymisation

The data come from a fleet of 24 medium twin-engine helicopters in offshore transport service between January 2024 and March 2026. Data sharing was authorised by the data owner on condition of anonymisation. Before release:

- aircraft registrations are replaced by fixed codes `AC-01` to `AC-24`, which do not encode exposure rank; the aircraft type is replaced by `OMTH`;
- locations and bases are replaced by codes `LOC-xx`;
- company names (operators, customers, manufacturers), installation names and registrations in free-text fields are replaced by the tokens `[COMPANY]`, `[LOCATION]`, `[INSTALLATION]` and `[AIRCRAFT]`;
- technicians' names, licence numbers and sign-off remarks are removed, and personal names in free text are replaced by `[PERSON]`;
- aircraft serial numbers and the "Removed By" field are removed.

Part numbers are kept, because they are common to several aircraft types. Raw records and the re-identification maps are not distributed.

## Licences

Code (`ramsc/`, `scripts/`): MIT licence (`LICENSE`). Data and supplementary material: CC BY 4.0 (`LICENSE-DATA.md`).

## Contact

Antonio Celio Pereira de Mesquita, Aerospace Logistics Engineering Laboratory (AeroLogLab), Instituto Tecnológico de Aeronáutica (ITA), São José dos Campos, Brazil. celio@ita.br, ORCID [0000-0002-3145-9987](https://orcid.org/0000-0002-3145-9987)
