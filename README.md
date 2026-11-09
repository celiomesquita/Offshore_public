# Offshore helicopter maintenance records: data and code for reproducibility

Replication package for the revised manuscript

> A. C. P. de Mesquita, *From Offshore Maintenance Records to Fleet Priorities: Evidence Limits and Joint Policies*, submitted to *Reliability Engineering & System Safety* (manuscript JRESS-D-26-04044, revision).

The package contains the anonymised operational data, the analysis code, the generated results and the supplementary tables (S1–S9). Every analysis reported in the revised manuscript can be rerun from the data in `data/`.

## Contents

| Path | Content |
|---|---|
| `data/` | Anonymised operator extracts: `hours_flown.xlsx` (flight logs), `removals.xlsx` (component removals), `OMTH_tasks.xlsx` (work-order tasks) |
| `config/public/aircraft_id_map.csv` | Pseudonymised aircraft identifiers with total flight hours and exposure band |
| `ramsc/` | Python package: panel construction, METRIC with corrected expected backorders, frequency–consequence priority, missing-work bounds, joint age–stock simulator |
| `scripts/` | One script per analysis; `scripts/run_all.py` runs the whole pipeline in order |
| `tests/` | Unit tests (METRIC identities, priority, missing-work bounds, joint simulator, event construction) |
| `analysis_outputs/` | Results generated from `data/` (CSV/JSON) |
| `latex/manuscript/tables`, `latex/manuscript/figures` | Generated tables and figures |
| `supplementary/` | Supplementary material (Tables S1–S9): `supplementary.pdf` and LaTeX sources |
| `docs/` | Pre-specified protocols for the rolling-origin, priority, missing-work and joint-policy experiments |

## Reproducing the results

Tested with Python 3.14 on Windows; the versions used are pinned in `requirements.txt`.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt     # Windows: .venv\Scripts\pip
python scripts/run_all.py                     # full pipeline, about 4 minutes
python scripts/run_all.py --skip-simulation   # empirical analyses only
python -m pytest tests
```

Each script can also be run individually from the repository root with `PYTHONPATH=.:scripts`.

Running the pipeline on the anonymised data reproduces all results files in `analysis_outputs/revision` exactly, as obtained with the original confidential records. Three remarks:

- Removal-count ties in the descriptive ATA and component Pareto tables may be listed in a different order than in the manuscript.
- The tables in `latex/manuscript/tables` are generated drafts; some were edited for layout in the manuscript. The CSV files are the reference values.
- `analysis_outputs/revision/pillar_dependency_inputs.csv` contains the original pillar scores by ATA chapter from the composite of the original submission, which the revision withdraws. It is distributed as a frozen derived input to the correlation table and is not rebuilt.

## Map from manuscript to scripts

| Manuscript element | Script |
|---|---|
| Panel, event dataset, work completeness | `build_panel.py`, `build_revision_event_consequences.py`, `audit_revision_selection.py` |
| Pareto concentration, NB panel, maintainability table | `export_r1_pareto.py`, `export_r2_pareto.py`, `fit_nb_panel.py`, `export_m1_maintainability.py` |
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

Part numbers are kept, because they are common to several aircraft types. Raw records and the re-identification maps are not distributed. The released files were checked automatically for registrations, company, location and installation names, ICAO codes, original identifiers and personal names.

## Licences

- Code (`ramsc/`, `scripts/`, `tests/`): MIT licence, see `LICENSE`.
- Data, results, supplementary material and documentation: Creative Commons Attribution 4.0 International (CC BY 4.0), see `LICENSE-DATA.md`.

## Citation

Please cite the article and this repository; see `CITATION.cff`.

## Contact

Antonio Celio Pereira de Mesquita — Aerospace Logistics Engineering Laboratory (AeroLogLab), Instituto Tecnológico de Aeronáutica (ITA), São José dos Campos, Brazil — celio@ita.br — ORCID [0000-0002-3145-9987](https://orcid.org/0000-0002-3145-9987)
