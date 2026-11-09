"""Availability analysis: METRIC calibration and scenario runs (Step 4 / Tables A-1, A-2, Figure A-F)."""

from __future__ import annotations

import math
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import poisson

from ramsc.metric import (
    calculate_pipeline_and_demand_rate,
    demand_cdf,
    expected_backorders,
    immediate_fill_rate,
    solve_metric,
)
from ramsc.reliability_nb import panel_nb_alpha
from ramsc.panel import filter_tracked_unscheduled_mechanical, load_raw_datasets
from ramsc.models import Base, MetricSolution, Part

# ---------------------------------------------------------------------------
# Fleet base parameters (OMTH offshore fleet)
# ---------------------------------------------------------------------------
TOTAL_HOURS: float = 33_486.6
ASSETS: int = 24
PERIOD_MONTHS: int = 27
STUDY_START = pd.Timestamp("2024-01-01")
STUDY_END_EXCLUSIVE = pd.Timestamp("2026-04-01")
PERIOD_CLOCK_HOURS: float = (STUDY_END_EXCLUSIVE - STUDY_START).total_seconds() / 3600
DUTY_CYCLE: float = TOTAL_HOURS / (PERIOD_CLOCK_HOURS * ASSETS)   # ≈ 0.053

# Lead-time assumptions (days): depot repair time + transport time.
DRT_DAYS: float = 30.0       # baseline depot repair time
DTRANS_DAYS: float = 5.0     # baseline transport time
DRT_STD: float = 0.0
DTRANS_STD: float = 0.0

# AOG day-rate sensitivity (USD/day); mid assumption.
AOG_DAY_RATE_MID: float = 20_000.0
GROUNDED_COST_MID: float = AOG_DAY_RATE_MID / 24.0   # USD per hour

TOP_N_PARTS: int = 20
SENSITIVITY_MAX_STOCK_LEVEL: int = 500

# Scenario S-B lead-time sensitivity (depot repair days, transport days).
LEADTIME_SB_SCENARIOS: dict[str, tuple[float, float]] = {
    "Short LT (20/5 d)": (20.0, 5.0),
    "Baseline LT (30/5 d)": (30.0, 5.0),
    "Long LT (40/10 d)": (40.0, 10.0),
}


def _make_base(
    drt: float = DRT_DAYS,
    dtrans: float = DTRANS_DAYS,
    grounded: float = GROUNDED_COST_MID,
) -> Base:
    return Base(
        id=1,
        name="OMTH offshore fleet",
        dtrans=dtrans,
        assets=ASSETS,
        duty_cycle=DUTY_CYCLE,
        grounded=grounded,
        dtrans_std=DTRANS_STD,
    )


def load_parts(
    root: Path,
    top_n: int = TOP_N_PARTS,
    *,
    drt_days: float = DRT_DAYS,
) -> List[Part]:
    """Load top-N repairables from the part Pareto CSV and calibrate METRIC inputs.

    lambda_j = rate_1000h / 1000 (failures per fleet flight hour per aircraft-hour norm).
    cost_j   = std_cost / removals (mean observed replacement cost per event).
    qpa      = 1 for all parts (conservative; flag if qpa > 1 is known).
    drt      = DRT_DAYS baseline; sensitivity tested externally.
    """
    csv = root / "analysis_outputs" / "part_pareto_tracked_unscheduled.csv"
    df = pd.read_csv(csv).head(top_n)
    df = df[df["std_cost"] > 0].copy()
    df["lambda_j"] = df["rate_1000h"] / 1000.0
    df["cost_per_removal"] = df["std_cost"] / df["removals"]

    parts = []
    for _, row in df.iterrows():
        part_num = str(row["Part #"])
        desc = str(row["Part Description"])[:22]
        parts.append(
            Part(
                name=f"{part_num} ({desc})",
                cost=float(row["cost_per_removal"]),
                lambda_=float(row["lambda_j"]),
                qpa=1,
                drt=drt_days,
                drt_std=DRT_STD,
            )
        )
    return parts


def baseline_metrics(base: Base, parts: List[Part]) -> pd.DataFrame:
    """Compute EBO and fill rate at stock = 0 for all parts (no investment)."""
    pipeline, demand_rate = calculate_pipeline_and_demand_rate(base, parts)
    rows = []
    for part, D, dr in zip(parts, pipeline, demand_rate):
        ebo0 = expected_backorders(0, D)
        fr0 = immediate_fill_rate(0, D)
        rows.append(
            {
                "part": part.name,
                "lambda_j": part.lambda_,
                "cost_j": part.cost,
                "pipeline_D": round(D, 4),
                "demand_rate": round(dr, 6),
                "stock_s0": 0,
                "EBO_s0": round(ebo0, 4),
                "FR_s0": round(fr0, 4),
            }
        )
    return pd.DataFrame(rows)


def run_scenarios(
    base: Base,
    parts: List[Part],
    budgets: dict[str, float],
    fill_rates: dict[str, float],
) -> dict[str, MetricSolution]:
    """Run all METRIC scenarios and return a results dict keyed by scenario name."""
    solutions: dict[str, MetricSolution] = {}

    for name, budget in budgets.items():
        solutions[name] = solve_metric(
            base,
            parts,
            budget=budget,
            constraint_priority="budget",
            use_cost_weighting=True,
        )

    for name, fr in fill_rates.items():
        solutions[name] = solve_metric(
            base,
            parts,
            budget=float("inf"),
            minimum_fill_rate=fr,
            constraint_priority="min_fr",
            use_cost_weighting=True,
        )

    return solutions


def scenario_comparison_table(
    solutions: dict[str, MetricSolution],
    scenario_labels: dict[str, str],
) -> pd.DataFrame:
    """Build Table A-2: scenario-level comparison."""
    rows = []
    for key, label in scenario_labels.items():
        sol = solutions[key]
        fleet_fr = (
            min(p.fill_rate for p in sol.parts) if sol.parts else 0.0
        )
        rows.append(
            {
                "scenario": label,
                "total_investment": round(sol.total_cost, 0),
                "total_EBO": round(sol.sum_ebo, 3),
                "min_fill_rate": round(fleet_fr, 4),
                "Ao": round(sol.operational_availability, 4),
                "grounded_cost": round(sol.grounded_cost, 0),
            }
        )
    return pd.DataFrame(rows)


def part_detail_table(sol: MetricSolution, parts: List[Part]) -> pd.DataFrame:
    """Build Table A-1: per-part METRIC results for one scenario."""
    cost_map = {p.name: p.cost for p in parts}
    rows = []
    for pr in sol.parts:
        rows.append(
            {
                "part": pr.name,
                "cost_j": round(cost_map.get(pr.name, 0.0), 0),
                "pipeline_D": round(pr.pipeline, 4),
                "stock_level": pr.stock,
                "EBO": round(pr.ebo, 4),
                "fill_rate": round(pr.fill_rate, 4),
                "investment": round(pr.stock * cost_map.get(pr.name, 0.0), 0),
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# LaTeX writers
# ---------------------------------------------------------------------------

def write_a1_latex(table: pd.DataFrame, output_path: Path, scenario_label: str) -> None:
    """Write Table A-1 (per-part METRIC results) as a LaTeX fragment."""
    lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\small",
        f"\\caption{{Per-part METRIC results under scenario {scenario_label}. "
        "Pipeline $D_{{ij}}$ is the expected number of units in the repair--transport cycle. "
        "Stock level is the recommended on-hand quantity; fill rate is $P(X \\leq s)$ under Poisson pipeline. "
        "Investment is stock level $\\times$ cost per removal.}",
        "\\label{tab:a1-metric-parts}",
        "\\resizebox{\\linewidth}{!}{%",
        "\\begin{tabular}{@{}lrrrrrr@{}}",
        "\\toprule",
        "Part & Cost (\\$) & Pipeline $D$ & Stock & EBO & Fill rate & Investment (\\$) \\\\",
        "\\midrule",
    ]
    for row in table.itertuples(index=False):
        lines.append(
            f"\\texttt{{{row.part}}} & {row.cost_j:,.0f} & {row.pipeline_D:.4f} & "
            f"{row.stock_level} & {row.EBO:.4f} & {row.fill_rate:.4f} & {row.investment:,.0f} \\\\"
        )
    lines.extend([
        "\\midrule",
        f"\\multicolumn{{6}}{{l}}{{Total investment}} & {table['investment'].sum():,.0f} \\\\",
        "\\bottomrule",
        "\\end{tabular}%",
        "}",
        "\\end{table}",
    ])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_a2_latex(table: pd.DataFrame, output_path: Path) -> None:
    """Write Table A-2 (scenario comparison) as a LaTeX fragment."""
    lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{METRIC scenario comparison: stock investment, expected backorders, "
        "minimum fill rate, operational availability, and estimated grounded cost. "
        "Lead-time assumptions: depot repair time 30~days, transport 5~days. "
        "AOG day-rate assumption: \\$20{,}000/day (mid scenario).}",
        "\\label{tab:a2-metric-scenarios}",
        "\\begin{tabular}{@{}lrrrr@{}}",
        "\\toprule",
        "Scenario & Investment (\\$) & Total EBO & Min. FR & $A_o$ \\\\",
        "\\midrule",
    ]
    for row in table.itertuples(index=False):
        lines.append(
            f"{row.scenario} & {row.total_investment:,.0f} & {row.total_EBO:.3f} & "
            f"{row.min_fill_rate:.4f} & {row.Ao:.4f} \\\\"
        )
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\par\\smallskip",
        "{\\footnotesize \\textit{Notes:} Min.\\ FR = minimum fill rate across all modelled parts. "
        "$A_o$ assumes a series-reliability structure in which any modelled part failure "
        "contributes to system unavailability (stated explicitly as a bounding assumption). "
        "Baseline: zero stock on all parts.}",
        "\\end{table}",
    ])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_af_figure(
    solutions: dict[str, MetricSolution],
    scenario_labels: dict[str, str],
    output_path: Path,
) -> None:
    """Write Figure A-F: cost-availability frontier across greedy trajectory."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    colors = ["#4C72B0", "#C44E52", "#55A868", "#8172B2", "#CCB974"]

    for ax, (y_key, y_label) in zip(
        axes,
        [("trajectory_ao", "Operational availability $A_o$"),
         ("trajectory_fill_rate", "Minimum fill rate")],
    ):
        for (key, label), color in zip(scenario_labels.items(), colors):
            sol = solutions[key]
            costs = sol.trajectory_costs
            values = getattr(sol, y_key)
            if costs and values:
                ax.plot(
                    [c / 1_000 for c in costs],
                    values,
                    label=label,
                    color=color,
                    linewidth=1.6,
                )
        ax.set_xlabel("Cumulative stock investment (\\$k)")
        ax.set_ylabel(y_label)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

    fig.suptitle(
        "METRIC cost--availability frontier\n"
        "BCR-weighted greedy allocation; top-20 parts by removal rate",
        fontsize=10,
    )
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def part_level_demand_diagnostic(root: Path, top_n: int = TOP_N_PARTS) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Summarise monthly part-level demand dispersion for the METRIC top-N parts."""
    _, removals, _ = load_raw_datasets(root)
    mech = filter_tracked_unscheduled_mechanical(removals).copy()
    mech["month"] = pd.to_datetime(
        mech["Removed Date_dt"], dayfirst=True, errors="coerce"
    ).dt.to_period("M")
    months = pd.period_range(mech["month"].min(), mech["month"].max(), freq="M")

    parts_df = pd.read_csv(root / "analysis_outputs" / "part_pareto_tracked_unscheduled.csv").head(top_n)
    rows: list[dict[str, object]] = []
    pooled_counts: list[int] = []
    for part_number in parts_df["Part #"].astype(str):
        part_counts = (
            mech.loc[mech["Part #"].astype(str) == part_number]
            .groupby("month")
            .size()
            .reindex(months, fill_value=0)
        )
        values = part_counts.to_numpy(dtype=float)
        pooled_counts.extend(values.astype(int).tolist())
        mean_count = float(values.mean())
        var_count = float(values.var(ddof=1)) if len(values) > 1 else 0.0
        alpha_mom = max((var_count - mean_count) / (mean_count ** 2), 0.0) if mean_count > 0 else 0.0
        rows.append(
            {
                "part_number": part_number,
                "monthly_failures": int(values.sum()),
                "months": int(len(values)),
                "mean_monthly_count": round(mean_count, 4),
                "variance_monthly_count": round(var_count, 4),
                "variance_to_mean": round(var_count / mean_count, 4) if mean_count > 0 else 0.0,
                "alpha_mom": round(alpha_mom, 4),
                "zero_month_fraction_observed": round(float((values == 0).mean()), 4),
                "zero_month_fraction_poisson": round(float(np.exp(-mean_count)), 4) if mean_count > 0 else 1.0,
                "max_monthly_count": int(values.max()) if len(values) else 0,
            }
        )

    summary = pd.DataFrame(rows).sort_values("monthly_failures", ascending=False).reset_index(drop=True)
    pooled = np.asarray(pooled_counts, dtype=int)
    pooled_mu = float(pooled.mean()) if len(pooled) else 0.0
    max_bin = 6
    dist_rows: list[dict[str, object]] = []
    for k in range(max_bin):
        dist_rows.append(
            {
                "bin": str(k),
                "observed_cells": int((pooled == k).sum()),
                "poisson_expected_cells": round(float(len(pooled) * poisson.pmf(k, pooled_mu)), 2),
                "pooled_mean": round(pooled_mu, 4),
            }
        )
    dist_rows.append(
        {
            "bin": f">={max_bin}",
            "observed_cells": int((pooled >= max_bin).sum()),
            "poisson_expected_cells": round(float(len(pooled) * (1.0 - poisson.cdf(max_bin - 1, pooled_mu))), 2),
            "pooled_mean": round(pooled_mu, 4),
        }
    )
    return summary, pd.DataFrame(dist_rows)


def write_part_level_poisson_figure(
    summary: pd.DataFrame,
    distribution: pd.DataFrame,
    output_path: Path,
    panel_alpha: float,
) -> None:
    """Write observed-vs-Poisson part-level demand diagnostic figure."""
    weighted_alpha = float(np.average(summary["alpha_mom"], weights=summary["monthly_failures"]))
    bins = distribution["bin"].astype(str).tolist()
    x = np.arange(len(bins))

    fig, ax = plt.subplots(figsize=(7.6, 4.5))
    ax.bar(x - 0.18, distribution["observed_cells"], width=0.36, label="Observed part-month cells", color="#4C72B0")
    ax.bar(x + 0.18, distribution["poisson_expected_cells"], width=0.36, label="Poisson expected", color="#C44E52")
    ax.set_xticks(x)
    ax.set_xticklabels(bins)
    ax.set_xlabel("Monthly removals per modelled part")
    ax.set_ylabel("Part-month cells")
    ax.set_title("Part-level demand dispersion for METRIC top-20 repairables", fontsize=10, fontweight="bold")
    ax.text(
        0.98,
        0.95,
        f"Weighted part-level $\\alpha$={weighted_alpha:.2f}\nPanel NB $\\alpha$={panel_alpha:.1f}",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#BBBBBB", "alpha": 0.9},
    )
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def nb_sensitivity_comparison(
    base: Base,
    parts: List[Part],
    *,
    nb_alpha: float,
    target_fill_rate: float = 0.85,
    max_stock_level: int = SENSITIVITY_MAX_STOCK_LEVEL,
) -> pd.DataFrame:
    """Compare Poisson vs NB pipeline demand for Scenario S-B (min fill rate)."""
    common = dict(
        budget=float("inf"),
        minimum_fill_rate=target_fill_rate,
        constraint_priority="min_fr",
        use_cost_weighting=True,
        max_stock_level=max_stock_level,
    )
    sol_poisson = solve_metric(base, parts, demand_model="poisson", **common)
    sol_nb = solve_metric(
        base,
        parts,
        demand_model="negbin",
        nb_alpha=nb_alpha,
        **common,
    )

    def _row(label: str, sol: MetricSolution, alpha: float) -> dict[str, object]:
        min_fr = min(p.fill_rate for p in sol.parts) if sol.parts else 0.0
        return {
            "demand_model": label,
            "nb_alpha": alpha,
            "total_investment": round(sol.total_cost, 0),
            "total_EBO": round(sol.sum_ebo, 3),
            "min_fill_rate": round(min_fr, 4),
            "Ao": round(sol.operational_availability, 4),
        }

    return pd.DataFrame(
        [
            _row("Poisson pipeline", sol_poisson, 0.0),
            _row("NB pipeline", sol_nb, nb_alpha),
        ]
    )


def part_stock_delta_table(
    sol_poisson: MetricSolution,
    sol_nb: MetricSolution,
    parts: List[Part],
) -> pd.DataFrame:
    """Per-part stock differences between Poisson and NB S-B solutions."""
    cost_map = {p.name: p.cost for p in parts}
    nb_map = {p.name: p for p in sol_nb.parts}
    rows = []
    for pr in sol_poisson.parts:
        nb = nb_map.get(pr.name)
        if nb is None:
            continue
        delta_stock = nb.stock - pr.stock
        if delta_stock == 0:
            continue
        rows.append(
            {
                "part": pr.name,
                "stock_poisson": pr.stock,
                "stock_nb": nb.stock,
                "delta_stock": delta_stock,
                "delta_investment": round(delta_stock * cost_map.get(pr.name, 0.0), 0),
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return frame.sort_values("delta_investment", ascending=False).reset_index(drop=True)


def write_a3_latex(table: pd.DataFrame, output_path: Path, nb_alpha: float) -> None:
    """Write Table A-3 (Poisson vs NB S-B sensitivity) as a LaTeX fragment."""
    lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{METRIC Scenario~S-B sensitivity to overdispersed pipeline demand. "
        "Both runs target a minimum fill rate of 85\\% across the top-20 repairables using "
        "BCR-weighted greedy allocation. \\rev{The Negative Binomial (NB) run is a conservative stress test: it retains the Poisson "
        f"pipeline means $D_{{ij}}$ but replaces the demand distribution with "
        f"$\\mathrm{{Var}}(X)=\\mu+\\alpha\\mu^2$ using $\\alpha={nb_alpha:.1f}$ "
        "from the fleet-panel NB model (Table~\\ref{tab:r3-nb-panel}).}}",
        "\\label{tab:a3-metric-nb-sensitivity}",
        "\\begin{tabular}{@{}lrrrr@{}}",
        "\\toprule",
        "Demand model & Investment (\\$) & Total EBO & Min.\\ FR & $A_o$ \\\\",
        "\\midrule",
    ]
    for row in table.itertuples(index=False):
        if row.nb_alpha > 0:
            model_label = f"NB pipeline ($\\alpha={row.nb_alpha:.1f}$)"
        else:
            model_label = row.demand_model
        lines.append(
            f"{model_label} & {row.total_investment:,.0f} & {row.total_EBO:.3f} & "
            f"{row.min_fill_rate:.4f} & {row.Ao:.4f} \\\\"
        )
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\par\\smallskip",
        "{\\footnotesize \\textit{Note:} Mean pipeline exposure $D_{ij}$ is unchanged; "
        "only the tail thickness of pipeline demand differs. \\rev{Part-level monthly demand dispersion for the same top-20 repairables is much smaller (weighted method-of-moments $\\alpha=0.32$; Figure~\\ref{fig:a-part-poisson-diagnostic}), so the panel-$\\alpha$ NB case is interpreted as an upper-bound stress test rather than a co-primary stock policy.} Lead-time and AOG assumptions "
        "match Table~\\ref{tab:a2-metric-scenarios}. Sensitivity runs allow up to 500 units per repairable "
        "(versus 169 in the baseline optimiser) so that the 85\\% fill-rate target remains "
        "feasible under heavy-tailed demand.}",
        "\\end{table}",
    ])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def leadtime_sb_sensitivity_table(root: Path) -> pd.DataFrame:
    """Run Scenario S-B (85% min fill rate) under alternative lead-time assumptions."""
    rows: list[dict[str, object]] = []
    for label, (drt_days, dtrans_days) in LEADTIME_SB_SCENARIOS.items():
        base = _make_base(dtrans=dtrans_days)
        parts = load_parts(root, drt_days=drt_days)
        sol = solve_metric(
            base,
            parts,
            budget=float("inf"),
            minimum_fill_rate=0.85,
            constraint_priority="min_fr",
            use_cost_weighting=True,
        )
        rows.append(
            {
                "scenario": label,
                "drt_days": drt_days,
                "dtrans_days": dtrans_days,
                "total_investment": round(sol.total_cost, 0),
                "total_EBO": round(sol.sum_ebo, 3),
                "min_fill_rate": round(min(r.fill_rate for r in sol.parts), 4),
                "Ao": round(sol.operational_availability, 4),
            }
        )
    return pd.DataFrame(rows)


def write_a4_latex(table: pd.DataFrame, output_path: Path) -> None:
    """Write Table A-4 (lead-time sensitivity for Scenario S-B)."""
    lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\small",
        "\\caption{METRIC Scenario~S-B (85\\% minimum fill rate) sensitivity to depot repair "
        "and transport lead times. Poisson pipeline demand; other assumptions match "
        "Table~\\ref{tab:a2-metric-scenarios}.}",
        "\\label{tab:a4-metric-leadtime}",
        "\\resizebox{\\linewidth}{!}{%",
        "\\begin{tabular}{@{}lrrrrrr@{}}",
        "\\toprule",
        "Scenario & DRT (d) & DTrans (d) & Investment (\\$) & Total EBO & Min.\\ FR & $A_o$ \\\\",
        "\\midrule",
    ]
    for row in table.itertuples(index=False):
        lines.append(
            f"{row.scenario} & {row.drt_days:.0f} & {row.dtrans_days:.0f} & "
            f"{row.total_investment:,.0f} & {row.total_EBO:.3f} & "
            f"{row.min_fill_rate:.4f} & {row.Ao:.4f} \\\\"
        )
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}%",
        "}",
        "\\par\\smallskip",
        "{\\footnotesize \\textit{Note:} Shorter lead times reduce pipeline exposure $D_{ij}$ "
        "and therefore stock investment required to meet the 85\\% fill-rate constraint. "
        "All values are modelled METRIC outputs, not measured fleet availability.}",
        "\\end{table}",
    ])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_leadtime_sensitivity(root: Path | None = None) -> dict:
    """Export Table A-4 and CSV for lead-time Scenario S-B sensitivity."""
    base_root = root or Path(__file__).resolve().parent.parent
    table = leadtime_sb_sensitivity_table(base_root)

    out_public = base_root / "analysis_outputs" / "public"
    out_tables = base_root / "latex" / "manuscript" / "tables"
    out_figures = base_root / "latex" / "manuscript" / "figures"
    out_public.mkdir(parents=True, exist_ok=True)

    table.to_csv(out_public / "table_a4_metric_leadtime.csv", index=False)
    write_a4_latex(table, out_tables / "table_a4_metric_leadtime.tex")

    return {"table": table}


def export_nb_sensitivity(root: Path | None = None) -> dict:
    """Run Poisson vs NB Scenario S-B comparison and export Table A-3."""
    base_root = root or Path(__file__).resolve().parent.parent
    base = _make_base()
    parts = load_parts(base_root)
    nb_alpha = panel_nb_alpha(base_root)

    comparison = nb_sensitivity_comparison(base, parts, nb_alpha=nb_alpha)
    part_dispersion, part_distribution = part_level_demand_diagnostic(base_root)
    sol_poisson = solve_metric(
        base,
        parts,
        budget=float("inf"),
        minimum_fill_rate=0.85,
        constraint_priority="min_fr",
        use_cost_weighting=True,
        demand_model="poisson",
        max_stock_level=SENSITIVITY_MAX_STOCK_LEVEL,
    )
    sol_nb = solve_metric(
        base,
        parts,
        budget=float("inf"),
        minimum_fill_rate=0.85,
        constraint_priority="min_fr",
        use_cost_weighting=True,
        demand_model="negbin",
        nb_alpha=nb_alpha,
        max_stock_level=SENSITIVITY_MAX_STOCK_LEVEL,
    )
    stock_delta = part_stock_delta_table(sol_poisson, sol_nb, parts)

    out_public = base_root / "analysis_outputs" / "public"
    out_tables = base_root / "latex" / "manuscript" / "tables"
    out_figures = base_root / "latex" / "manuscript" / "figures"
    out_public.mkdir(parents=True, exist_ok=True)

    comparison.to_csv(out_public / "table_a3_metric_nb_sensitivity.csv", index=False)
    stock_delta.to_csv(out_public / "table_a3_metric_nb_stock_delta.csv", index=False)
    part_dispersion.to_csv(out_public / "metric_part_level_dispersion.csv", index=False)
    part_distribution.to_csv(out_public / "metric_part_level_poisson_distribution.csv", index=False)
    write_a3_latex(comparison, out_tables / "table_a3_metric_nb_sensitivity.tex", nb_alpha)
    write_part_level_poisson_figure(
        part_dispersion,
        part_distribution,
        out_figures / "fig_a_part_poisson_diagnostic.pdf",
        nb_alpha,
    )

    return {
        "nb_alpha": nb_alpha,
        "comparison": comparison,
        "stock_delta": stock_delta,
        "part_dispersion": part_dispersion,
        "part_distribution": part_distribution,
        "sol_poisson": sol_poisson,
        "sol_nb": sol_nb,
    }


# ---------------------------------------------------------------------------
# Main export function
# ---------------------------------------------------------------------------

def export_availability(root: Path | None = None) -> dict:
    """Run all METRIC scenarios and export Tables A-1, A-2, Figure A-F, and CSVs."""
    base_root = root or Path(__file__).resolve().parent.parent
    base = _make_base()
    parts = load_parts(base_root)

    # Scenarios
    budgets = {"S-A": 50_000.0, "S-D": 200_000.0}
    fill_rates = {"S-B": 0.85, "S-C": 0.95}
    all_scenario_keys = ["S-A", "S-B", "S-C", "S-D"]
    scenario_labels = {
        "S-A": "S-A (budget \\$50k)",
        "S-B": "S-B (min FR 85\\%)",
        "S-C": "S-C (min FR 95\\%)",
        "S-D": "S-D (budget \\$200k)",
    }

    solutions = run_scenarios(base, parts, budgets, fill_rates)

    # Tables
    baseline_df = baseline_metrics(base, parts)
    detail_sb = part_detail_table(solutions["S-B"], parts)
    comparison = scenario_comparison_table(solutions, scenario_labels)

    # Prepend baseline row to comparison
    bl_min_fr = float(baseline_df["FR_s0"].min())
    bl_ebo = float(baseline_df["EBO_s0"].sum())
    pipeline, demand_rate = calculate_pipeline_and_demand_rate(base, parts)
    from ramsc.metric import _system_operating_time, _operational_availability
    ot = _system_operating_time(base, parts)
    dr_total = sum(demand_rate)
    wt = bl_ebo / dr_total if dr_total > 0 else 0.0
    ao_bl, _, _ = _operational_availability(ot, wt, base.duty_cycle)
    baseline_row = pd.DataFrame([{
        "scenario": "Baseline (stock = 0)",
        "total_investment": 0.0,
        "total_EBO": round(bl_ebo, 3),
        "min_fill_rate": round(bl_min_fr, 4),
        "Ao": round(ao_bl, 4),
        "grounded_cost": round(base.grounded * bl_ebo, 0),
    }])
    comparison = pd.concat([baseline_row, comparison], ignore_index=True)

    # Output paths
    out_public = base_root / "analysis_outputs" / "public"
    out_tables = base_root / "latex" / "manuscript" / "tables"
    out_figures = base_root / "latex" / "manuscript" / "figures"
    out_figures = base_root / "latex" / "manuscript" / "figures"

    out_public.mkdir(parents=True, exist_ok=True)
    baseline_df.to_csv(out_public / "table_a1_metric_baseline.csv", index=False)
    detail_sb.to_csv(out_public / "table_a1_metric_sb.csv", index=False)
    comparison.to_csv(out_public / "table_a2_metric_scenarios.csv", index=False)

    write_a1_latex(detail_sb, out_tables / "table_a1_metric_parts.tex", "S-B (min FR 85\\%)")
    write_a2_latex(comparison, out_tables / "table_a2_metric_scenarios.tex")
    write_af_figure(solutions, scenario_labels, out_figures / "fig_a_frontier.pdf")

    return {
        "base": base,
        "parts": parts,
        "baseline": baseline_df,
        "solutions": solutions,
        "comparison": comparison,
        "detail_sb": detail_sb,
    }
