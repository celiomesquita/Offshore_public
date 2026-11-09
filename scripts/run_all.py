"""Run the full revision pipeline from the anonymised data in data/.

Usage:  python scripts/run_all.py [--skip-simulation]
Outputs: analysis_outputs/ (CSV/JSON), latex/manuscript/{tables,figures} (generated tables and figures)
and supplementary/revision_tables.tex (Supplementary Tables S1--S9).
"""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
DATA_STEPS = ['build_panel', 'build_revision_event_consequences', 'build_doc_task_link', 'build_part_pareto',
              'export_r1_pareto', 'export_r2_pareto', 'fit_nb_panel', 'export_m1_maintainability',
              ]
# analysis_outputs/revision/pillar_dependency_inputs.csv (original pillar scores by ATA chapter, from the
# withdrawn composite of the original submission) is distributed as a frozen derived input; it is not rebuilt.
ANALYSIS_STEPS = ['run_revision_count_forecasts', 'run_revision_rolling_baselines', 'run_revision_priority_backtest',
                  'audit_revision_selection', 'run_revision_missing_work', 'run_revision_weight_tradeoff',
                  'run_revision_granularity', 'run_revision_component_dependence', 'run_revision_demand_process',
                  'run_revision_metric', 'run_revision_metric_nb', 'run_revision_exact_stock',
                  'audit_revision_stock_optimality', 'run_revision_priority_generator']
SIMULATION_STEPS = ['run_revision_joint_pilot', 'run_revision_joint_expanded', 'run_revision_joint_sensitivity']
EXPORT_STEPS = ['export_revision_verified_tables', 'export_revision_supplement', 'export_joint_sensitivity', 'export_revision_decision_figures', 'export_revision_framework']


def run(step):
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join([str(ROOT), str(ROOT / 'scripts')]), 'PYTHONIOENCODING': 'utf-8'}
    start = time.time()
    subprocess.run([sys.executable, str(ROOT / 'scripts' / f'{step}.py')], cwd=ROOT, env=env, check=True,
                   stdout=subprocess.DEVNULL)
    print(f'{step:42s} {time.time() - start:6.1f} s')
    if step == 'build_panel':  # revision scripts read the panel from analysis_outputs/revision
        target = ROOT / 'analysis_outputs/revision'
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / 'analysis_outputs/public/panel_aircraft_ata_month.csv', target)


if __name__ == '__main__':
    for folder in ('analysis_outputs/revision', 'analysis_outputs/public', 'latex/manuscript/tables', 'latex/manuscript/figures'):
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    steps = DATA_STEPS + ANALYSIS_STEPS + ([] if '--skip-simulation' in sys.argv else SIMULATION_STEPS) + EXPORT_STEPS
    for step in steps:
        run(step)
