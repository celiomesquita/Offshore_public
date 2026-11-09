"""Rolling Poisson/NB2 and rate comparisons specified in MR07."""
from pathlib import Path
import hashlib
import json
import warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'analysis_outputs/revision'
SOURCE = OUT/'panel_aircraft_ata_month.csv'


def run():
    panel = pd.read_csv(SOURCE)
    panel['period'] = pd.PeriodIndex(panel.month, freq='M')
    atas = sorted(panel.ata2.unique())
    records, fits = [], []
    for horizon in (3, 6):
        origins = pd.period_range('2024-12', panel.period.max()-horizon, freq='M')
        for origin in origins:
            past = panel.loc[panel.period.le(origin)]
            hours = past.drop_duplicates(['pt_id', 'month']).groupby('pt_id').H_im.sum()
            eligible = hours.index[hours.ge(500)]
            subset = panel.loc[panel.pt_id.isin(eligible) & panel.H_im.gt(0)]
            history = subset.loc[subset.period.le(origin)]
            future = subset.loc[subset.period.gt(origin) & subset.period.le(origin+horizon)]
            train = history.groupby(['period', 'ata2']).agg(y=('Y_iam', 'sum'),
                                                         hours=('H_im', 'sum')).reset_index()
            test = future.groupby(['period', 'ata2']).agg(y=('Y_iam', 'sum'),
                                                        hours=('H_im', 'sum')).reset_index()
            active = train.groupby('ata2').y.sum().loc[lambda x: x.gt(0)].index.tolist()
            train_active = train.loc[train.ata2.isin(active)].copy()
            test_active = test.loc[test.ata2.isin(active)].copy()

            def design(frame):
                indicators = np.column_stack([frame.ata2.eq(ata).astype(float) for ata in active])
                trend = np.array([(p.ordinal-origin.ordinal)/12 for p in frame.period])
                return np.column_stack([indicators, trend])

            x, xnew = design(train_active), design(test_active)
            offset = np.log(train_active.hours.to_numpy())
            offset_new = np.log(test_active.hours.to_numpy())
            y = train_active.y.to_numpy()
            poisson = sm.GLM(y, x, offset=offset, family=sm.families.Poisson()).fit()
            for method in ('poisson_trend', 'nb2_trend'):
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter('always')
                    if method == 'poisson_trend':
                        fitted = poisson
                        converged = bool(poisson.converged)
                        alpha = 0.0
                    else:
                        model = sm.NegativeBinomial(y, x, offset=offset, loglike_method='nb2')
                        fitted = model.fit(start_params=np.r_[poisson.params, .1],
                                           method='lbfgs', maxiter=500, disp=False)
                        converged = bool(fitted.mle_retvals['converged'])
                        alpha = float(fitted.params[-1])
                    prediction = fitted.predict(xnew, offset=offset_new)
                valid = converged and np.isfinite(prediction).all() and (prediction >= 0).all()
                fits.append(dict(origin=str(origin), horizon=horizon, method=method,
                                 converged=converged, valid=bool(valid), alpha=alpha,
                                 inactive_atas=json.dumps([int(a) for a in sorted(set(atas)-set(active))]),
                                 warnings=' | '.join(str(w.message) for w in caught)))
                predicted = pd.Series(prediction, index=test_active.index).groupby(test_active.ata2).sum()
                forecast = predicted.reindex(atas, fill_value=0) if valid else pd.Series(np.nan, index=atas)
                append_rows(records, forecast, test, origin, horizon, method, len(eligible), valid)
            for method, data in [('cumulative_rate', train),
                                 ('recent_6m_rate', train.loc[train.period.gt(origin-6)])]:
                rates = data.groupby('ata2').y.sum()/data.groupby('ata2').hours.sum()
                forecast = (rates*test.groupby('ata2').hours.sum()).reindex(atas, fill_value=0)
                append_rows(records, forecast, test, origin, horizon, method, len(eligible), True)
            print(f'horizon={horizon} origin={origin} complete', flush=True)
    result = pd.DataFrame(records)
    result.to_csv(OUT/'rolling_count_forecasts.csv', index=False)
    fit_log = pd.DataFrame(fits)
    fit_log.to_csv(OUT/'rolling_count_fit_log.csv', index=False)
    summary = []
    for (horizon, origin, method), frame in result.groupby(['horizon', 'origin', 'method']):
        valid = bool(frame.valid.all())
        error = frame.forecast-frame.observed
        summary.append(dict(horizon=horizon, origin=origin, method=method, valid=valid,
                            mae=error.abs().mean() if valid else np.nan,
                            rmse=np.sqrt((error**2).mean()) if valid else np.nan,
                            bias_total=error.sum() if valid else np.nan,
                            spearman=spearmanr(frame.forecast, frame.observed).statistic if valid else np.nan))
    summary = pd.DataFrame(summary)
    summary.to_csv(OUT/'rolling_count_summary.csv', index=False)
    manifest = dict(panel_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                    design='ATA intercepts + common linear annual trend; monthly fleet counts; log exposure offset',
                    nb='NB2 MLE, shared alpha, L-BFGS, maxiter=500, Poisson start',
                    conditioning='realised future flight hours; registered positive-exposure cells only',
                    inference='descriptive, overlapping origins; no significance or predictive interval claim',
                    fit_count=len(fit_log), invalid_fits=int((~fit_log.valid).sum()),
                    numpy=np.__version__, pandas=pd.__version__, statsmodels=sm.__version__)
    (OUT/'rolling_count_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(summary.groupby(['horizon', 'method'])[['mae', 'rmse', 'bias_total']].mean().to_string())
    print(f'Invalid fits: {manifest["invalid_fits"]}')


def append_rows(records, forecast, test, origin, horizon, method, eligible, valid):
    observed = test.groupby('ata2').y.sum()
    for ata, value in forecast.items():
        records.append(dict(origin=str(origin), horizon=horizon, method=method, ata2=int(ata),
                            forecast=float(value), observed=int(observed.get(ata, 0)),
                            eligible_aircraft=eligible, valid=bool(valid)))


if __name__ == '__main__':
    run()
