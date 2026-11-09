"""Predefined synthetic scenarios; freeze all candidates before new-seed evaluation."""
from dataclasses import asdict, replace
from pathlib import Path
import json
import math
import pandas as pd
from scipy.stats import t
from ramsc.joint_policy import JointInputs, simulate_policy

OUT=Path(__file__).resolve().parents[1]/'analysis_outputs/revision'
base=JointInputs()
mean_life=base.scale*math.gamma(1+1/base.shape)
scenarios={'base':base}
for shape in (.7,1.,3.):
    scenarios[f'shape_{shape:g}']=replace(base,shape=shape,scale=mean_life/math.gamma(1+1/shape))
for days in (0.,5.,60.):
    scenarios[f'lead_{days:g}']=replace(base,lead_days=days)
for cost in (0.,200.,20000.):
    scenarios[f'downcost_{cost:g}']=replace(base,down_cost_per_day=cost)
for price in (100.,10000.):
    scenarios[f'price_{price:g}']=replace(base,part_price=price)
ages=(60.,90.,120.,150.,180.,210.,240.,300.,360.,float('inf'))
stocks=tuple(range(13))+(16,24)
choices, training_rows, frozen = {}, [], {}
for name,p in scenarios.items():
    rows=[simulate_policy(p,a,s,seed) for a in ages for s in stocks for seed in range(8)]
    frame=pd.DataFrame(rows)
    frame['scenario']=name
    training_rows.append(frame)
    means=frame.groupby(['age_days','stock']).annual_cost.mean()
    best=means.idxmin()
    policies={'corrective_adapted':(float('inf'),int(means.loc[float('inf')].idxmin())),
              'joint_adapted':(float(best[0]),int(best[1])),
              'base_transferred':(150.,6)}
    choices[name]=policies
    frozen[name]=dict(parameters=asdict(p),policies={k:dict(
        age_days='infinity' if math.isinf(a) else a,stock=s) for k,(a,s) in policies.items()},
        joint_stock_boundary=bool(best[1]==max(stocks)),
        joint_age_lower_boundary=bool(best[0]==min(ages)),
        mean_operating_lifetime= p.scale*math.gamma(1+1/p.shape))
    print(name+' selection complete',flush=True)
pd.concat(training_rows).to_csv(OUT/'joint_sensitivity_training.csv',index=False)
(OUT/'joint_sensitivity_frozen.json').write_text(json.dumps(dict(
    protocol='docs/MR06_SENSITIVITY_PROTOCOL.md',training_seeds=list(range(8)),
    evaluation_seeds=list(range(2000,2050)),scenarios=frozen),indent=2)+'\n')
rows=[]
for name,p in scenarios.items():
    for policy,(age,stock) in choices[name].items():
        for seed in range(2000,2050):
            r=simulate_policy(p,age,stock,seed)
            r.update(scenario=name,policy=policy)
            for kind in ('failures','preventive','demands'):
                r['annual_'+kind]=r[kind]*365/p.measurement_days
            rows.append(r)
    print(name+' evaluation complete',flush=True)
result=pd.DataFrame(rows)
result.to_csv(OUT/'joint_sensitivity_runs.csv',index=False)
means=result.groupby(['scenario','policy']).mean(numeric_only=True)
means.to_csv(OUT/'joint_sensitivity_means.csv')
contrasts=[]
for name,frame in result.groupby('scenario'):
    cost=frame.pivot(index='seed',columns='policy',values='annual_cost')
    availability=frame.pivot(index='seed',columns='policy',values='availability')
    for policy in ('joint_adapted','base_transferred'):
        delta=cost[policy]-cost.corrective_adapted
        half=t.ppf(.975,49)*delta.std(ddof=1)/math.sqrt(50)
        contrasts.append(dict(scenario=name,policy=policy,mean_difference=delta.mean(),
                              ci_low=delta.mean()-half,ci_high=delta.mean()+half,
                              relative_difference=delta.mean()/cost.corrective_adapted.mean(),
                              availability_difference=(availability[policy]-availability.corrective_adapted).mean()))
comparison=pd.DataFrame(contrasts)
comparison.to_csv(OUT/'joint_sensitivity_contrasts.csv',index=False)
print(comparison.to_string(index=False))
