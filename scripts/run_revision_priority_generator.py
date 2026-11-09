"""R1.4 (MR08): known-truth synthetic evaluation of frequency versus frequency--consequence priority.

Synthetic fleets are generated with chapter-level removal rates lambda_a, mean labour m_a and mean
parts value c_a. Removals in a training and a three-month test period are Poisson; per-event labour
is exponential and parts value lognormal. Labour is observed only for a subset of events under a
specified observation mechanism. Each method selects k chapters from the common universe with
observed consequences in training, as in the empirical protocol. Because the full test burden is
known, selections are scored against the true burden, including unobserved work.

Factors (one at a time around a base case calibrated to the order of magnitude of the fleet):
consequence heterogeneity, rate--consequence dependence, observation mechanism, data volume,
number of chapters and demand overdispersion.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis_outputs/revision'
REPS, K, W = 1000, 3, 0.5
BASE = dict(chapters=20, monthly_removals=63.0, train_months=12, sigma_lambda=1.2, sigma_m=0.75,
            sigma_c=1.0, rho=0.0, observation='mcar', q=0.22, nb_alpha=0.0, work_shape=1.0,
            outcome='true')
SCENARIOS = [('base', {})]
SCENARIOS += [(f'sigma_m={v}', dict(sigma_m=v)) for v in (0.25, 1.25)]
SCENARIOS += [(f'sigma_c={v}', dict(sigma_c=v)) for v in (0.5, 1.5)]
SCENARIOS += [(f'rho={v}', dict(rho=v)) for v in (-0.6, 0.6)]
SCENARIOS += [('observation=complete', dict(observation='complete', q=1.0)),
              ('observation=mnar_system', dict(observation='mnar_system')),
              ('observation=mnar_event', dict(observation='mnar_event'))]
SCENARIOS += [(f'train_months={v}', dict(train_months=v)) for v in (6, 24)]
SCENARIOS += [(f'monthly_removals={v}', dict(monthly_removals=v)) for v in (15.0, 250.0)]
SCENARIOS += [(f'chapters={v}', dict(chapters=v)) for v in (10, 40)]
SCENARIOS += [('nb_alpha=1', dict(nb_alpha=1.0)), ('work_cv=2.5', dict(work_shape=0.16)),
              ('outcome=observed', dict(outcome='observed'))]
# Calibrated to the fleet: 27 chapters, dispersion of chapter rates and values, rate--labour correlation 0.4,
# event-level labour CV about 2.5, and a near-unobserved leading chapter (main rotor: 1.3% complete).
EMPIRICAL = dict(chapters=27, sigma_lambda=1.5, sigma_m=0.5, sigma_c=1.5, rho=0.4, work_shape=0.16)
SCENARIOS += [('fleet-like, true outcome', EMPIRICAL),
              ('fleet-like, observed outcome', {**EMPIRICAL, 'outcome': 'observed'}),
              ('fleet-like, leading-chapter gap, observed outcome',
               {**EMPIRICAL, 'outcome': 'observed', 'observation': 'leading_gap'})]


def counts(rng, mean, alpha):
    if alpha <= 0:
        return rng.poisson(mean)
    return rng.poisson(rng.gamma(1 / alpha, alpha * mean))


def observe(rng, p, chapter, work, m_true, lead=None):
    """Return a boolean mask of events whose labour is observed."""
    if p['observation'] == 'complete':
        return np.ones(len(work), bool)
    if p['observation'] == 'mcar':
        return rng.random(len(work)) < p['q']
    if p['observation'] == 'leading_gap':  # the highest-rate chapter is almost never complete
        qa = np.full(len(m_true), p['q']); qa[lead] = 0.013
        return rng.random(len(work)) < qa[chapter]
    if p['observation'] == 'mnar_system':  # high-labour chapters are less completely recorded
        z = (np.log(m_true) - np.log(m_true).mean()) / np.log(m_true).std()
        qa = 1 / (1 + np.exp(-(np.log(p['q'] / (1 - p['q'])) - 1.5 * z)))
        return rng.random(len(work)) < qa[chapter]
    # mnar_event: long interventions are less likely to be completely recorded
    scale = work / m_true[chapter]
    qe = p['q'] * np.exp(-0.7 * (scale - 1))
    return rng.random(len(work)) < np.clip(qe, 0, 1)


def simulate(rng, p):
    A = p['chapters']
    z = rng.standard_normal((A, 3))
    log_lam = p['sigma_lambda'] * z[:, 0]
    lam = np.exp(log_lam); lam *= p['monthly_removals'] / lam.sum()
    zm = p['rho'] * z[:, 0] + np.sqrt(1 - p['rho'] ** 2) * z[:, 1]
    m = 6.0 * np.exp(p['sigma_m'] * zm - p['sigma_m'] ** 2 / 2)
    c = 30000.0 * np.exp(p['sigma_c'] * z[:, 2] - p['sigma_c'] ** 2 / 2)

    def period(months):
        n = counts(rng, lam * months, p['nb_alpha'])
        chap = np.repeat(np.arange(A), n)
        work = rng.gamma(p['work_shape'], m[chap] / p['work_shape'])
        parts = c[chap] * np.exp(rng.normal(-0.5, 1.0, len(chap)))
        return n, chap, work, parts

    n_tr, ch_tr, w_tr, c_tr = period(p['train_months'])
    lead = int(np.argmax(lam))
    obs = observe(rng, p, ch_tr, w_tr, m, lead)
    n_te, ch_te, w_te, c_te = period(3)
    if p['outcome'] == 'observed':  # score only work that would be recorded, as in the empirical evaluation
        w_te = np.where(observe(rng, p, ch_te, w_te, m, lead), w_te, 0.0)
    m_hat = np.bincount(ch_tr[obs], w_tr[obs], A) / np.maximum(np.bincount(ch_tr[obs], minlength=A), 1)
    c_hat = np.bincount(ch_tr, c_tr, A) / np.maximum(n_tr, 1)
    universe = (np.bincount(ch_tr[obs], minlength=A) > 0) & (n_tr > 0)
    if universe.sum() <= K:
        return None
    m_ref, c_ref = w_tr[obs].mean(), c_tr.mean()
    rate = n_tr / p['train_months']
    true_work, true_parts = np.bincount(ch_te, w_te, A), np.bincount(ch_te, c_te, A)
    target = W * true_work / m_ref + (1 - W) * true_parts / c_ref
    scores = {'frequency': rate, 'consequence': rate * (W * m_hat / m_ref + (1 - W) * c_hat / c_ref),
              'oracle': lam * (W * m / m_ref + (1 - W) * c / c_ref)}
    u = np.flatnonzero(universe)
    den = target[u].sum()
    if den <= 0:
        return None
    out = {}
    for name, s in scores.items():
        top = u[np.argsort(-s[u], kind='stable')[:K]]
        out[name] = target[top].sum() / den
        out[name + '_work'] = true_work[top].sum() / max(true_work[u].sum(), 1e-12)
        out[name + '_parts'] = true_parts[top].sum() / max(true_parts[u].sum(), 1e-12)
    out['universe_share'] = n_te[u].sum() / max(n_te.sum(), 1)
    return out


def run():
    rows = []
    for idx, (name, change) in enumerate(SCENARIOS):
        p = {**BASE, **change}
        rng = np.random.default_rng(20261109 + idx)
        res = [r for r in (simulate(rng, p) for _ in range(REPS)) if r is not None]
        df = pd.DataFrame(res)
        d = 100 * (df.consequence - df.frequency)
        rows.append(dict(scenario=name, valid_reps=len(df), frequency=100 * df.frequency.mean(),
                         consequence=100 * df.consequence.mean(), oracle=100 * df.oracle.mean(),
                         diff_pp=d.mean(), diff_se=d.std(ddof=1) / np.sqrt(len(d)),
                         share_better=(d > 1e-9).mean(), share_worse=(d < -1e-9).mean(),
                         diff_work_pp=100 * (df.consequence_work - df.frequency_work).mean(),
                         diff_parts_pp=100 * (df.consequence_parts - df.frequency_parts).mean(),
                         oracle_gain_pp=100 * (df.oracle - df.frequency).mean(),
                         universe_share=df.universe_share.mean()))
    summ = pd.DataFrame(rows)
    summ.to_csv(OUT / 'priority_generator_summary.csv', index=False)
    json.dump(dict(base=BASE, scenarios=SCENARIOS, reps=REPS, k=K, w=W,
                   outcome='share of true test burden (w=0.5 normalised work + parts value) in the common universe'),
              open(OUT / 'priority_generator_manifest.json', 'w'), indent=2)
    pd.set_option('display.width', 200)
    print(summ.round(2).to_string(index=False))
    write_table(summ)
    return summ


LABELS = {'base': 'Base case', 'sigma_m=0.25': 'Labour heterogeneity $\\sigma_m=0.25$',
          'sigma_m=1.25': 'Labour heterogeneity $\\sigma_m=1.25$', 'sigma_c=0.5': 'Parts-value heterogeneity $\\sigma_c=0.5$',
          'sigma_c=1.5': 'Parts-value heterogeneity $\\sigma_c=1.5$', 'rho=-0.6': 'Rate--labour correlation $-0.6$',
          'rho=0.6': 'Rate--labour correlation $0.6$', 'observation=complete': 'All work observed',
          'observation=mnar_system': 'Less complete in high-labour chapters', 'observation=mnar_event': 'Long interventions less complete',
          'train_months=6': 'Six training months', 'train_months=24': '24 training months',
          'monthly_removals=15.0': '15 removals per month', 'monthly_removals=250.0': '250 removals per month',
          'chapters=10': '10 chapters', 'chapters=40': '40 chapters', 'nb_alpha=1': 'Overdispersed demand ($\\alpha=1$)',
          'work_cv=2.5': 'Heavy-tailed labour (CV 2.5)', 'outcome=observed': 'Only recorded work scored',
          'fleet-like, true outcome': 'Fleet-like, true burden', 'fleet-like, observed outcome': 'Fleet-like, recorded work scored',
          'fleet-like, leading-chapter gap, observed outcome': 'Fleet-like, leading chapter unrecorded'}


def write_table(s):
    L = [r'\begin{table}[htbp]', r'\centering', r'\small',
         r'\caption{Known-truth synthetic fleets: coverage of the true test burden by the top three chapters (\%) and difference between the consequence priority ($w=0.5$) and frequency (percentage points).}',
         r'\label{tab:priority-generator}', r'\resizebox{\linewidth}{!}{%', r'\begin{tabular}{lrrrrrrrr}', r'\toprule',
         r'Scenario & Freq. & Cons. & Oracle & Diff. (SE) & Better & Worse & Work diff. & Parts diff. \\', r'\midrule']
    for r in s.itertuples():
        L.append(f'{LABELS[r.scenario]} & {r.frequency:.1f} & {r.consequence:.1f} & {r.oracle:.1f} & {r.diff_pp:+.1f} ({r.diff_se:.1f}) & '
                 f'{100*r.share_better:.0f}\\% & {100*r.share_worse:.0f}\\% & {r.diff_work_pp:+.1f} & {r.diff_parts_pp:+.1f} \\\\')
    L += [r'\bottomrule', r'\end{tabular}}', r'\par\smallskip',
          r'{\footnotesize 1,000 synthetic fleets per scenario; one factor changed from the base case (20 chapters, 63 removals per month, 12 training months, lognormal dispersion 1.2 for rates, 0.75 for labour and 1.0 for parts value, 22\% of work observed at random). Fleet-like scenarios use 27 chapters, dispersions 1.5/0.5/1.5, rate--labour correlation 0.4 and labour CV 2.5. Better/Worse: share of fleets in which the consequence priority covers more/less of the combined burden. Work and parts differences refer to each outcome separately. Oracle: selection by the true expected burden.}',
          r'\end{table}']
    (ROOT / 'latex/manuscript/tables/table_priority_generator.tex').write_text(chr(10).join(L) + chr(10), encoding='utf-8')


if __name__ == '__main__':
    run()
