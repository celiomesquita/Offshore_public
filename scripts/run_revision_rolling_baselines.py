"""Retrospective rolling exposure-rate baselines under the MR07 protocol."""
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.stats import spearmanr

root = Path(__file__).resolve().parents[1]
out = root/'analysis_outputs/revision'
panel = pd.read_csv(out/'panel_aircraft_ata_month.csv')
panel['period'] = pd.PeriodIndex(panel.month, freq='M')
atas = sorted(panel.ata2.unique())
origins = pd.period_range('2024-12', '2025-12', freq='M')
rows = []
for origin in origins:
    train = panel.loc[panel.period.le(origin)]
    exposure = train.drop_duplicates(['pt_id','month']).groupby('pt_id').H_im.sum()
    eligible = exposure.index[exposure.ge(500)]
    test = panel.loc[panel.period.gt(origin) & panel.period.le(origin+3)
                     & panel.pt_id.isin(eligible) & panel.H_im.gt(0)]
    observed = test.groupby('ata2').Y_iam.sum().reindex(atas, fill_value=0)
    future_hours = test.drop_duplicates(['pt_id','month']).H_im.sum()
    for method, history in [('cumulative_rate',train),
                             ('recent_6m_rate',train.loc[train.period.gt(origin-6)])]:
        history = history.loc[history.pt_id.isin(eligible) & history.H_im.gt(0)]
        hours = history.drop_duplicates(['pt_id','month']).H_im.sum()
        counts = history.groupby('ata2').Y_iam.sum().reindex(atas, fill_value=0)
        forecast = counts/hours*future_hours
        for ata in atas:
            rows.append({'origin':str(origin),'horizon_months':3,'method':method,
                         'ata2':ata,'eligible_aircraft':len(eligible),
                         'train_hours':hours,'test_hours':future_hours,
                         'forecast':forecast[ata],'observed':observed[ata]})
result = pd.DataFrame(rows)
result.to_csv(out/'rolling_rate_forecasts.csv', index=False)
summary=[]
for (origin, method), frame in result.groupby(['origin','method']):
    error = frame.forecast-frame.observed
    summary.append({'origin':origin,'method':method,'mae':error.abs().mean(),
                    'rmse':np.sqrt((error**2).mean()),'bias_total':error.sum(),
                    'forecast_total':frame.forecast.sum(),'observed_total':frame.observed.sum(),
                    'spearman':spearmanr(frame.forecast,frame.observed).statistic})
summary = pd.DataFrame(summary)
summary.to_csv(out/'rolling_rate_summary.csv',index=False)
print(summary.groupby('method')[['mae','rmse','bias_total','spearman']].mean().to_string())
print('Retrospective, overlapping horizons; means are descriptive, no significance test.')
