"""R2.6: decision-oriented figures for the priority comparison and the joint-policy sensitivity."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis_outputs/revision'
FIG = ROOT / 'latex/manuscript/figures'
BLUE, ORANGE, INK, MUTED, GRID = '#2a78d6', '#eb6834', '#0b0b0b', '#52514e', '#e4e3df'
plt.rcParams.update({'font.size': 8.5, 'axes.edgecolor': MUTED, 'axes.labelcolor': INK, 'xtick.color': MUTED,
                     'ytick.color': MUTED, 'axes.spines.top': False, 'axes.spines.right': False,
                     'font.family': 'serif', 'pdf.fonttype': 42})


def priority_figure():
    g = pd.read_csv(OUT / 'granularity_priority_by_origin.csv')
    base = g[g.method.eq('frequency')].set_index(['unit', 'k', 'origin'])
    d = g[g.method.ne('frequency')].copy()
    d = d.join(base[['work', 'parts']], on=['unit', 'k', 'origin'], rsuffix='_f')
    d['w'] = d.method.str[1:].astype(float)
    d['dwork'], d['dparts'] = 100 * (d.work - d.work_f), 100 * (d.parts - d.parts_f)
    series = [(('ata2', 3), 'ATA chapter, top 3', BLUE, -0.035), (('part', 5), 'Part number, top 5', ORANGE, 0.035)]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0), sharey=True)
    rng = np.random.default_rng(1)
    for ax, col, title in zip(axes, ('dwork', 'dparts'), ('Recorded work', 'Standard parts value')):
        ax.axhline(0, color=MUTED, lw=0.8)
        ax.grid(axis='y', color=GRID, lw=0.6); ax.set_axisbelow(True)
        for (key, label, colour, off) in series:
            s = d[(d.unit == key[0]) & (d.k == key[1])]
            x = s.w + off + rng.uniform(-0.012, 0.012, len(s))
            ax.scatter(x, s[col], s=9, color=colour, alpha=0.45, lw=0)
            m = s.groupby('w')[col].mean()
            ax.plot(m.index + off, m.values, color=colour, lw=2, marker='o', ms=5,
                    markeredgecolor='white', markeredgewidth=1, label=label)
        ax.set_title(title, color=INK, fontsize=9)
        ax.set_xticks([0, .25, .5, .75, 1]); ax.set_xlabel('Labour weight $w$')
    axes[0].set_ylabel('Coverage difference from frequency (pp)')
    axes[0].legend(frameon=False, loc='lower left')
    fig.tight_layout()
    fig.savefig(FIG / 'fig_priority_coverage.pdf'); plt.close(fig)


def joint_figure():
    c = pd.read_csv(OUT / 'joint_sensitivity_contrasts.csv')
    order = list(dict.fromkeys(c.scenario))
    names = {'downcost': 'Downtime loss USD {}/day', 'lead': 'Purchase lead time {} days',
             'price': 'Part price USD {}', 'shape': 'Weibull shape {}'}
    labels = {s: 'Base case' if s == 'base' else names[s.split('_')[0]].format(f"{float(s.split('_')[1]):,.10g}")
              for s in order}
    nz = c[c.relative_difference.ne(0)]
    comparator = (nz.mean_difference / nz.relative_difference).groupby(nz.scenario).first()
    fig, ax = plt.subplots(figsize=(7.0, 0.32 * len(order) + 0.9))
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.grid(axis='x', color=GRID, lw=0.6); ax.set_axisbelow(True)
    for policy, colour, off, label in (('joint_adapted', BLUE, -0.15, 'Adapted joint policy'),
                                       ('base_transferred', ORANGE, 0.15, 'Base policy transferred unchanged')):
        s = c[c.policy.eq(policy)].set_index('scenario').reindex(order)
        rel = 100 * s.relative_difference
        scale = 100 / comparator.reindex(order)
        y = np.arange(len(order)) + off
        ax.errorbar(rel, y, xerr=[rel - scale * s.ci_low, scale * s.ci_high - rel], fmt='o', color=colour,
                    ms=5, mec='white', mew=1, elinewidth=1.5, capsize=0, label=label)
    ax.set_yticks(np.arange(len(order))); ax.set_yticklabels([labels[s] for s in order])
    ax.invert_yaxis()
    ax.set_xlabel('Annual cost difference from the corrective-stock policy (%)')
    fig.legend(*ax.get_legend_handles_labels(), frameon=False, loc='upper center', ncol=2)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(FIG / 'fig_joint_sensitivity.pdf'); plt.close(fig)
    return order


if __name__ == '__main__':
    priority_figure()
    print(joint_figure())
