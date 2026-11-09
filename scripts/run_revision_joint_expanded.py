"""Select on pilot seeds, freeze policies, then evaluate new paired seeds."""
from dataclasses import asdict, replace
from pathlib import Path
import json
import math
import pandas as pd
from scipy.stats import t
from ramsc.joint_policy import JointInputs, simulate_policy

OUT=Path(__file__).resolve().parents[1]/'analysis_outputs/revision'
p=JointInputs()
ages=(60.,90.,120.,150.,180.,210.,240.,300.,360.,float('inf'))
stocks=tuple(range(13))+(16,24)
rows=[simulate_policy(p,a,s,seed) for a in ages for s in stocks for seed in range(8)]
training=pd.DataFrame(rows)
training.to_csv(OUT/'joint_expanded_training.csv',index=False)
means=training.groupby(['age_days','stock']).annual_cost.mean()
means.to_csv(OUT/'joint_expanded_training_means.csv')
best=means.idxmin()
policies={'corrective_no_stock':(float('inf'),0),
          'corrective_stock':(float('inf'),int(means.loc[float('inf')].idxmin())),
          'age_no_stock':(float(means.xs(0,level='stock').idxmin()),0),
          'joint_candidate':(float(best[0]),int(best[1]))}
serial={k:dict(age_days='infinity' if math.isinf(a) else a,stock=s)
        for k,(a,s) in policies.items()}
manifest=dict(protocol='docs/MR06_EXPANDED_PROTOCOL.md',parameters=asdict(p),
              training_seeds=list(range(8)),evaluation_seeds=list(range(1000,1050)),
              policies=serial,stock_upper_boundary=bool(best[1]==max(stocks)),
              status='frozen before independent evaluation; not an empirical recommendation')
(OUT/'joint_frozen_candidates.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Frozen policies:',json.dumps(serial),flush=True)
settings={'primary':(365.,3650.),'no_warmup':(0.,3650.),
          'long_warmup':(1095.,3650.),'long_horizon':(365.,7300.)}
rows=[]
for setting,(warmup,duration) in settings.items():
    inputs=replace(p,warmup_days=warmup,measurement_days=duration)
    for name,(age,stock) in policies.items():
        for seed in range(1000,1050):
            result=simulate_policy(inputs,age,stock,seed)
            result.update(setting=setting,policy=name)
            for kind in ('failures','preventive','demands'):
                result['annual_'+kind]=result[kind]*365/duration
            rows.append(result)
    print(setting+' complete',flush=True)
result=pd.DataFrame(rows)
result.to_csv(OUT/'joint_independent_runs.csv',index=False)
result.groupby(['setting','policy']).mean(numeric_only=True).to_csv(OUT/'joint_independent_means.csv')
contrasts=[]
for setting,frame in result.groupby('setting'):
    paired=frame.pivot(index='seed',columns='policy',values='annual_cost')
    for comparator in policies:
        if comparator=='joint_candidate':continue
        delta=paired.joint_candidate-paired[comparator]
        half=float(t.ppf(.975,len(delta)-1)*delta.std(ddof=1)/math.sqrt(len(delta)))
        contrasts.append(dict(setting=setting,comparator=comparator,replicates=len(delta),
                              mean_difference=delta.mean(),ci_low=delta.mean()-half,
                              ci_high=delta.mean()+half,paired_sd=delta.std(ddof=1),
                              relative_mean_difference=delta.mean()/paired[comparator].mean()))
comparison=pd.DataFrame(contrasts)
comparison.to_csv(OUT/'joint_independent_contrasts.csv',index=False)
print(comparison.to_string(index=False))
