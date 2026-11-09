"""Predefined synthetic MR06 pilot; candidate selection is exploratory."""
from dataclasses import asdict
from pathlib import Path
import json
import math
import pandas as pd
from ramsc.joint_policy import JointInputs, simulate_policy

out=Path(__file__).resolve().parents[1]/'analysis_outputs/revision'
p=JointInputs()
rows=[simulate_policy(p,age,stock,seed) for age in (60.,120.,180.,360.,float('inf'))
      for stock in (0,1,2,4,8) for seed in range(8)]
result=pd.DataFrame(rows)
result.to_csv(out/'joint_policy_pilot_runs.csv',index=False)
means=result.groupby(['age_days','stock']).mean(numeric_only=True)
means.to_csv(out/'joint_policy_pilot_means.csv')
best=means.annual_cost.idxmin()
corrective=means.loc[float('inf')].annual_cost.idxmin()
age_only=means.xs(0,level='stock').annual_cost.idxmin()
policies={'corrective_no_stock':(float('inf'),0),
          'corrective_stock':(float('inf'),int(corrective)),
          'age_no_stock':(float(age_only),0),'joint_grid_candidate':best}
baseline=float(means.loc[(float('inf'),0),'annual_cost'])
candidate=result.loc[result.age_days.eq(best[0])&result.stock.eq(best[1])].set_index('seed')
comparisons=[]
for name,(age,stock) in policies.items():
    ref=result.loc[result.age_days.eq(age)&result.stock.eq(stock)].set_index('seed')
    delta=candidate.annual_cost-ref.annual_cost
    n=max(30,math.ceil((1.96*delta.std(ddof=1)/(.01*baseline))**2))
    comparisons.append(dict(comparator=name,age_days=age,stock=stock,
                            pilot_annual_cost=ref.annual_cost.mean(),
                            candidate_minus_comparator=delta.mean(),paired_sd=delta.std(ddof=1),
                            indicative_new_repetitions=n))
comparison=pd.DataFrame(comparisons)
comparison.to_csv(out/'joint_policy_pilot_comparison.csv',index=False)
manifest=dict(parameters=asdict(p),seeds=list(range(8)),runs=len(rows),
              candidate_age_days='infinity' if math.isinf(best[0]) else float(best[0]),
              candidate_stock=int(best[1]),
              status='synthetic pilot; selected and evaluated on same seeds; not confirmatory',
              main_experiment='not run; RV01 mechanism review and independent seeds required')
(out/'joint_policy_pilot_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(comparison.to_string(index=False))
print(means.loc[best].to_string())
