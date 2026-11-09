"""Multiple-choice integer reference for the two empirical budget scenarios."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix
from ramsc.availability import _make_base, load_parts
from ramsc.metric import calculate_pipeline_and_demand_rate, expected_backorders, solve_metric

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'analysis_outputs/revision'
base, parts = _make_base(), load_parts(ROOT)
pipeline, rates = calculate_pipeline_and_demand_rate(base, parts)
rows = []
for label, budget in [('S-A', 50000), ('S-D', 200000)]:
    options = [(i, s) for i, p in enumerate(parts)
               for s in range(min(169, int(budget//p.cost))+1)]
    objective = np.array([expected_backorders(s, pipeline[i]) for i, s in options])
    matrix = lil_matrix((len(parts)+1, len(options)))
    for j, (i, s) in enumerate(options):
        matrix[i, j] = 1
        matrix[-1, j] = parts[i].cost*s/budget
    lower, upper = np.r_[np.ones(len(parts)), 0], np.ones(len(parts)+1)
    result = milp(objective, integrality=np.ones(len(options)),
                  bounds=Bounds(0, 1), constraints=LinearConstraint(matrix.tocsc(), lower, upper),
                  options={'time_limit':60, 'mip_rel_gap':1e-8})
    if result.x is None:
        raise RuntimeError(f'{label}: no feasible integer result: {result.message}')
    stock = np.zeros(len(parts), dtype=int)
    for (i, s), selected in zip(options, result.x):
        if selected > .5:
            stock[i] = s
    investment = sum(s*p.cost for s, p in zip(stock, parts))
    ebo = sum(expected_backorders(s, mu) for s, mu in zip(stock, pipeline))
    assert investment <= budget+1e-5
    assert abs(ebo-result.fun) < 1e-7
    heuristic = solve_metric(base, parts, budget=budget, use_cost_weighting=True)
    rows.append(dict(scenario=label, budget=budget, investment_usd=investment,
                     integer_ebo=ebo, heuristic_ebo=heuristic.sum_ebo,
                     heuristic_relative_gap=(heuristic.sum_ebo-ebo)/ebo,
                     solver_status=int(result.status), solver_message=result.message,
                     mip_gap=float(result.mip_gap), lower_bound=float(result.mip_dual_bound)))
    pd.DataFrame(dict(part=[p.name for p in parts], stock=stock,
                      pipeline=pipeline, unit_cost=[p.cost for p in parts])).to_csv(
                          OUT/f'metric_{label.lower()}_integer_stock.csv', index=False)
frame = pd.DataFrame(rows)
frame.to_csv(OUT/'metric_integer_comparison.csv', index=False)
(OUT/'metric_integer_manifest.json').write_text(json.dumps(dict(
    formulation='one stock level selected per part; sum cost <= budget; minimise sum EBO',
    demand='Poisson; same calibration and inputs as corrected heuristic',
    stock_cap=169, time_limit_seconds=60, requested_relative_gap=1e-8,
    interpretation='integer reference conditional on model and input data, not empirical operational benefit'
), indent=2)+'\n')
print(frame.to_string(index=False))
