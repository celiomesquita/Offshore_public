"""Compare the budget heuristic with enumeration on controlled small instances."""
from itertools import product
from pathlib import Path
import json
import numpy as np
import pandas as pd
from ramsc.metric import expected_backorders, solve_metric
from ramsc.models import Base, Part

root = Path(__file__).resolve().parents[1]
out = root / 'analysis_outputs/revision'
rng = np.random.default_rng(20261107)
cap = 8
stocks = np.array(list(product(range(cap+1), repeat=3)))
rows = []
base = Base(1, 'synthetic', 0, 1, 1, 0)
for case in range(60):
    means = rng.uniform(.1, 5, 3)
    costs = rng.integers(1, 11, 3)
    budget = int(rng.integers(5, 41))
    parts = [Part(str(i), float(c), float(mu)/24, 1, 1)
             for i, (mu, c) in enumerate(zip(means, costs))]
    table = np.array([[expected_backorders(s, mu) for s in range(cap+1)]
                      for mu in means])
    objectives = sum(table[i, stocks[:, i]] for i in range(3))
    feasible = stocks @ costs <= budget
    best_index = np.flatnonzero(feasible)[np.argmin(objectives[feasible])]
    result = solve_metric(base, parts, budget=budget, use_cost_weighting=True,
                          max_stock_level=cap)
    optimum = float(objectives[best_index])
    rows.append(dict(case=case, means=json.dumps(means.tolist()),
                     costs=json.dumps(costs.tolist()), budget=budget,
                     heuristic_stock=json.dumps([p.stock for p in result.parts]),
                     exact_stock=json.dumps(stocks[best_index].tolist()),
                     heuristic_ebo=result.sum_ebo, exact_ebo=optimum,
                     absolute_gap=result.sum_ebo-optimum,
                     relative_gap=(result.sum_ebo-optimum)/optimum))
frame = pd.DataFrame(rows)
assert frame.absolute_gap.min() >= -1e-10
frame.to_csv(out/'stock_enumeration_audit.csv', index=False)
manifest = dict(seed=20261107, cases=60, parts=3, stock_cap=cap,
                scope='controlled Poisson instances; not an empirical fleet optimality bound',
                nonoptimal_cases=int(frame.absolute_gap.gt(1e-10).sum()),
                maximum_absolute_gap=float(frame.absolute_gap.max()),
                maximum_relative_gap=float(frame.relative_gap.max()))
(out/'stock_enumeration_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(json.dumps(manifest, indent=2))
