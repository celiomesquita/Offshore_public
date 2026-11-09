"""Revised framework figure: evidence flow and indicator dependence (R2.6, R1.2, R4.1).

Replaces the original five-pillar composite workflow. Greyscale-safe fills; text carries
the meaning, colour only groups lanes.
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parents[1] / "latex" / "manuscript" / "figures" / "fig_framework.pdf"
EDGE, TEXT = "#37474F", "#1F2933"
FILL = {"emp": "#DCE7F2", "log": "#E6E1F2", "syn": "#F3E6D3", "dep": "#FFFFFF"}
NL = "\n"


def box(ax, x, y, w, h, title, lines, kind, dashed=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                fc=FILL[kind], ec=EDGE, lw=1.0, ls="--" if dashed else "-"))
    ax.text(x + w / 2, y + h - 0.13, title, ha="center", va="top", fontsize=8.6, weight="bold", color=TEXT)
    ax.text(x + w / 2, y + h - 0.42, NL.join(lines), ha="center", va="top", fontsize=7.2,
            color=TEXT, linespacing=1.3)


def arrow(ax, x0, y0, x1, y1, dashed=False, text=None):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=10,
                                 lw=1.0, color=EDGE, ls="--" if dashed else "-"))
    if text:
        ax.text((x0 + x1) / 2, (y0 + y1) / 2 + 0.1, text, ha="center", va="bottom", fontsize=6.8, linespacing=1.3,
                style="italic", color=TEXT)


fig, ax = plt.subplots(figsize=(7.6, 6.4))
ax.set_xlim(0, 10)
ax.set_ylim(0, 9.0)
ax.axis("off")
C1, W1, C2, W2, C3, W3 = 0.45, 2.1, 2.85, 3.4, 6.55, 3.35

for y, text in [(7.35, "Empirical records"), (3.85, "Assumed logistics"), (1.35, "Synthetic policy")]:
    ax.text(0.05, y, text, rotation=90, ha="left", va="center", fontsize=8, weight="bold", color=TEXT)

box(ax, C1, 6.55, W1, 1.6, "Linked records",
    ["flight logs, removals,", "work orders", "1,711 tracked", "unscheduled removals"], "emp")
box(ax, C2, 6.55, W2, 1.6, "Frequency and consequences",
    [r"frequency $\lambda_a$ (removals per FH)", r"work per event $m_a$ (complete cases)",
     r"parts value per event $c_a$", "missing work kept missing"], "emp")
box(ax, C3, 6.55, W3, 1.6, "Retrospective evaluation",
    ["13 rolling origins, top-3 selection", r"frequency vs $P_a(w)$, $w\in[0,1]$",
     "coverage of observed work", "and parts value; work envelopes"], "emp")
arrow(ax, C1 + W1, 7.35, C2, 7.35)
arrow(ax, C2 + W2, 7.35, C3, 7.35)

box(ax, C2, 4.75, W2, 1.55, "Totals repeat frequency",
    [r"total work $=\lambda_a m_a$", r"total parts value $=\lambda_a c_a$",
     r"zero-stock EBO $\propto \lambda_a$ (same lead time)",
     "normalisation cannot remove this"], "dep", dashed=True)
arrow(ax, C2 + W2 / 2, 6.55, C2 + W2 / 2, 6.25, dashed=True)

box(ax, C1, 3.0, W1, 1.7, "Assumed inputs",
    ["removal rates, QPA,", "standard values,", "35-day replenishment"], "log")
box(ax, C3, 3.0, W3, 1.7, "Corrected METRIC",
    [r"EBO$(s)=\mathrm{E}[(X-s)^+]$; fill $\Pr(X<s)$", "budget and service scenarios",
     "integer benchmark", "Poisson vs NB demand"], "log")
arrow(ax, C1 + W1, 3.85, C3, 3.85,
      text="pipeline = demand rate × lead time" + NL + "outputs not added to the priority")

box(ax, C1, 0.5, W1, 1.7, "Synthetic system",
    ["8 assets, Weibull lives,", "purchase lead time,", "explicit downtime cost"], "syn")
box(ax, C2, 0.5, W2, 1.7, "Joint age–stock selection",
    [r"replacement age $T$, base stock $s$", "150 policies, pilot seeds", "candidates frozen"], "syn")
box(ax, C3, 0.5, W3, 1.7, "Independent evaluation",
    ["50 new paired seeds", "12 one-factor scenarios", "adapted and transferred policies",
     "cost and availability"], "syn")
arrow(ax, C1 + W1, 1.35, C2, 1.35)
arrow(ax, C2 + W2, 1.35, C3, 1.35)

ax.text(5.2, 8.75, "Safety text indicators are excluded from all decision rules (no validated labels)",
        ha="center", va="center", fontsize=7.4, style="italic", color=TEXT)

OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, bbox_inches="tight")
fig.savefig(OUT.with_suffix(".png"), dpi=150, bbox_inches="tight")
print(OUT)
