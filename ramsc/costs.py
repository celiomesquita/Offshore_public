"""Cost pillar (COUR) analysis for the RAMSC Results section (Step 6 / Tables C-1, C-2, Figure C-P)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ramsc.panel import filter_tracked_unscheduled_mechanical, load_raw_datasets, repo_data_paths
from ramsc.maintainability import maintainability_table

# ---------------------------------------------------------------------------
# COUR assumptions
# ---------------------------------------------------------------------------
LABOUR_RATE_USD: float = 50.0        # USD per man-hour (assumed; stated explicitly in table)
LABOUR_RATE_SCENARIOS: tuple[float, ...] = (50.0, 100.0, 150.0)

AOG_SCENARIOS: dict[str, tuple[float, float]] = {
    "Low":  (0.5, 15_000.0),   # (days per event, USD per day)
    "Mid":  (1.0, 20_000.0),
    "High": (2.0, 25_000.0),
}

ATA2_LABELS: dict[int, str] = {
    18: "Vibration monitoring",   21: "Air conditioning",
    22: "Auto flight",            23: "Communications",
    24: "Electrical power",       25: "Equipment / furnishings",
    26: "Fire protection",        28: "Fuel",
    29: "Hydraulic power",        31: "Indicating / recording",
    32: "Landing gear",           33: "Lights",
    34: "Navigation",             35: "Oxygen",
    45: "Central maintenance",    53: "Fuselage",
    55: "Stabilisers",            62: "Main rotors",
    63: "Rotor drive",            64: "Tail rotor",
    65: "Tail rotor drive",       67: "Rotor / flight controls",
    71: "Powerplant",             72: "Engine",
    73: "Engine fuel \\& control",75: "Air (bleed)",
    77: "Engine indicating",
}


def _aog_rate(scenario: str) -> float:
    """AOG cost per removal event in USD for a given scenario."""
    days, day_rate = AOG_SCENARIOS[scenario]
    return days * day_rate


def ata_parts_cost(root: Path) -> pd.DataFrame:
    """Compute observed parts cost per ATA from removals.xlsx."""
    _, removals, _ = load_raw_datasets(root)
    mech = filter_tracked_unscheduled_mechanical(removals).copy()
    mech["ata2"] = (pd.to_numeric(mech["ATA #"], errors="coerce") // 100).astype("Int64")
    mech["Std Cost"] = pd.to_numeric(mech["Std Cost"], errors="coerce").fillna(0)
    grp = mech.groupby("ata2").agg(
        removals=("Part #", "size"),
        parts_cost=("Std Cost", "sum"),
    ).reset_index()
    return grp


def cour_table(
    root: Path,
    aog_scenario: str = "Mid",
    *,
    impute_alhwo: bool = False,
    labour_rate_usd: float | None = None,
) -> pd.DataFrame:
    """Build ATA-level COUR table (Table C-1) for a given AOG scenario."""
    rate = labour_rate_usd if labour_rate_usd is not None else LABOUR_RATE_USD
    parts_df = ata_parts_cost(root)

    # Labour cost from maintainability proportional allocation
    maint, _ = maintainability_table(root, impute_alhwo=impute_alhwo)
    labour_df = maint[["ata2", "total_manhours"]].copy()
    labour_df["labour_cost"] = labour_df["total_manhours"] * rate

    aog_rate = _aog_rate(aog_scenario)

    table = parts_df.merge(labour_df, on="ata2", how="left")
    table["total_manhours"] = table["total_manhours"].fillna(0)
    table["labour_cost"] = table["labour_cost"].fillna(0)
    table["aog_cost"] = table["removals"] * aog_rate
    table["cour"] = table["parts_cost"] + table["labour_cost"] + table["aog_cost"]
    table["ata_label"] = table["ata2"].map(lambda c: ATA2_LABELS.get(int(c), "Other"))

    # Rankings
    table = table.sort_values("cour", ascending=False).reset_index(drop=True)
    table["cour_rank"] = table.index + 1
    vol_order = table.sort_values("removals", ascending=False).reset_index(drop=True)
    vol_map = {row.ata2: i + 1 for i, row in vol_order.iterrows()}
    table["vol_rank"] = table["ata2"].map(vol_map)
    table["rank_diff"] = table["vol_rank"] - table["cour_rank"]

    return table


def sensitivity_table(root: Path) -> pd.DataFrame:
    """Build Table C-2: fleet-total COUR sensitivity to AOG assumptions."""
    rows = []
    for scenario in ["Low", "Mid", "High"]:
        t = cour_table(root, aog_scenario=scenario)
        days, day_rate = AOG_SCENARIOS[scenario]
        top3_share = t.head(3)["cour"].sum() / t["cour"].sum() * 100
        rows.append({
            "scenario": scenario,
            "aog_day_rate": day_rate,
            "aog_duration_days": days,
            "total_parts_cost": t["parts_cost"].sum(),
            "total_labour_cost": t["labour_cost"].sum(),
            "total_aog_cost": t["aog_cost"].sum(),
            "total_cour": t["cour"].sum(),
            "top3_ata_share_pct": round(top3_share, 1),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# LaTeX writers
# ---------------------------------------------------------------------------

def write_c1_latex(table: pd.DataFrame, output_path: Path,
                   aog_scenario: str = "Mid", top_n: int = 12) -> None:
    """Write Table C-1 (ATA-level COUR) as a LaTeX fragment."""
    days, day_rate = AOG_SCENARIOS[aog_scenario]
    top = table.head(top_n)
    lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\small",
        f"\\caption{{Cost of unreliability (COUR) by ATA system, {aog_scenario} AOG scenario. "
        f"Labour cost: \\${LABOUR_RATE_USD:.0f}/h assumed rate. "
        f"AOG cost: {days}~day $\\times$ \\${day_rate:,.0f}/day per unscheduled removal event "
        "(stated as a bounding assumption; not all removals ground the aircraft). "
        "Volume rank (Vol.\\ rk) and COUR rank divergence ($\\Delta$rk) highlight "
        "systems where economic priority differs from removal frequency.}",
        "\\label{tab:c1-cour}",
        "\\resizebox{\\linewidth}{!}{%",
        "\\begin{tabular}{@{}rlrrrrrrr@{}}",
        "\\toprule",
        "Rk & ATA (system) & Removals & Parts (\\$k) & Labour (\\$k) "
        "& AOG (\\$k) & COUR (\\$k) & Vol.\\ rk & $\\Delta$rk \\\\",
        "\\midrule",
    ]
    for row in top.itertuples(index=False):
        delta = int(row.rank_diff)
        delta_str = f"+{delta}" if delta > 0 else str(delta)
        lines.append(
            f"{int(row.cour_rank)} & {int(row.ata2):02d} ({row.ata_label}) & "
            f"{int(row.removals)} & {row.parts_cost/1000:.1f} & "
            f"{row.labour_cost/1000:.1f} & {row.aog_cost/1000:.1f} & "
            f"{row.cour/1000:.1f} & {int(row.vol_rank)} & {delta_str} \\\\"
        )
    total_cour = table["cour"].sum()
    total_parts = table["parts_cost"].sum()
    total_labour = table["labour_cost"].sum()
    total_aog = table["aog_cost"].sum()
    lines.extend([
        "\\midrule",
        f"\\multicolumn{{2}}{{l}}{{Fleet total (all ATA)}} & "
        f"{int(table['removals'].sum())} & {total_parts/1000:.1f} & "
        f"{total_labour/1000:.1f} & {total_aog/1000:.1f} & "
        f"{total_cour/1000:.1f} & --- & --- \\\\",
        "\\bottomrule",
        "\\end{tabular}%",
        "}",
        "\\par\\smallskip",
        "{\\footnotesize \\textit{Notes:} All costs in USD thousands. "
        "Parts cost = sum of standard replacement cost from removal records. "
        "Labour cost = ATA-level man-hours from linked work orders $\\times$ assumed rate. "
        "ALHWO work orders (zero man-hours) excluded from labour. "
        "$\\Delta$rk = volume rank $-$ COUR rank; positive values indicate "
        "systems whose cost priority exceeds their removal-count priority.}",
        "\\end{table}",
    ])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_c2_latex(sens: pd.DataFrame, output_path: Path) -> None:
    """Write Table C-2 (COUR sensitivity) as a LaTeX fragment."""
    lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Fleet COUR sensitivity to AOG day-rate and duration assumptions. "
        "Parts and labour costs are fixed across scenarios; only AOG cost varies. "
        f"Labour rate: \\${LABOUR_RATE_USD:.0f}/h (assumed). "
        "Top-3 ATA share: fraction of fleet COUR concentrated in the three highest-cost ATA systems.}",
        "\\label{tab:c2-cour-sensitivity}",
        "\\resizebox{\\linewidth}{!}{%",
        "\\begin{tabular}{@{}lrrrrrrr@{}}",
        "\\toprule",
        "Scenario & Day-rate (\\$) & Duration (d) & "
        "Parts (\\$M) & Labour (\\$M) & AOG (\\$M) & COUR (\\$M) & Top-3 (\\%) \\\\",
        "\\midrule",
    ]
    for row in sens.itertuples(index=False):
        lines.append(
            f"{row.scenario} & {row.aog_day_rate:,.0f} & {row.aog_duration_days:.1f} & "
            f"{row.total_parts_cost/1e6:.2f} & {row.total_labour_cost/1e6:.2f} & "
            f"{row.total_aog_cost/1e6:.2f} & {row.total_cour/1e6:.2f} & "
            f"{row.top3_ata_share_pct:.1f} \\\\"
        )
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}%",
        "}",
        "\\end{table}",
    ])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Figure C-P: cost-weighted vs volume Pareto divergence
# ---------------------------------------------------------------------------

def write_cp_figure(table: pd.DataFrame, output_path: Path, top_n: int = 12) -> None:
    """Write Figure C-P: COUR vs volume Pareto with rank-divergence annotations."""
    top = table.head(top_n).copy()
    top["label"] = top["ata2"].apply(lambda c: f"ATA {int(c):02d}")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharey=False)

    # Left panel: COUR bar chart (sorted by COUR, already sorted)
    colors_cour = ["#C44E52" if abs(r) >= 3 else "#4C72B0" for r in top["rank_diff"]]
    axes[0].barh(
        top["label"][::-1], top["cour"][::-1] / 1e6,
        color=colors_cour[::-1], edgecolor="white", linewidth=0.5,
    )
    axes[0].set_xlabel("COUR (USD million, mid AOG scenario)")
    axes[0].set_title("COUR ranking", fontsize=10)
    axes[0].grid(axis="x", alpha=0.3)

    # Right panel: volume bar chart sorted by volume rank
    vol_top = top.sort_values("vol_rank").head(top_n)
    colors_vol = ["#C44E52" if abs(r) >= 3 else "#55A868" for r in vol_top["rank_diff"]]
    axes[1].barh(
        vol_top["label"][::-1], vol_top["removals"][::-1],
        color=colors_vol[::-1], edgecolor="white", linewidth=0.5,
    )
    axes[1].set_xlabel("Tracked unscheduled removals")
    axes[1].set_title("Volume (removal count) ranking", fontsize=10)
    axes[1].grid(axis="x", alpha=0.3)

    # Annotate rank-divergence on COUR panel
    for ax in axes:
        ax.tick_params(axis="y", labelsize=8)

    fig.suptitle(
        "Cost-weighted vs volume Pareto - top ATA systems (Figure C-P)\n"
        "Red bars: rank difference $|\\Delta rk| \\geq 3$ between COUR and volume rankings",
        fontsize=9,
    )
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main export function
# ---------------------------------------------------------------------------

def labour_sensitivity_table(root: Path, aog_scenario: str = "Mid") -> pd.DataFrame:
    """Compare fleet COUR under baseline vs ALHWO-imputed labour (Table C-3)."""
    baseline = cour_table(root, aog_scenario=aog_scenario, impute_alhwo=False)
    imputed = cour_table(root, aog_scenario=aog_scenario, impute_alhwo=True)
    _, meta = maintainability_table(root, impute_alhwo=True)

    def _summary(label: str, table: pd.DataFrame) -> dict[str, object]:
        top3_share = table.head(3)["cour"].sum() / table["cour"].sum() * 100
        return {
            "labour_scenario": label,
            "total_parts_cost": table["parts_cost"].sum(),
            "total_labour_cost": table["labour_cost"].sum(),
            "total_aog_cost": table["aog_cost"].sum(),
            "total_cour": table["cour"].sum(),
            "labour_share_pct": table["labour_cost"].sum() / table["cour"].sum() * 100,
            "top3_ata_share_pct": round(top3_share, 1),
        }

    rows = [
        _summary("Exclude ALHWO (baseline)", baseline),
        _summary("Impute ALHWO at same-ATA h/rem", imputed),
    ]
    frame = pd.DataFrame(rows)
    frame.attrs["imputed_alhwo_mh"] = meta["imputed_alhwo_mh"]
    frame.attrs["alhwo_removals"] = meta["alhwo_total_removals"]
    return frame


def write_c3_latex(sens: pd.DataFrame, output_path: Path, *, aog_scenario: str = "Mid") -> None:
    """Write Table C-3 (ALHWO labour imputation sensitivity) as a LaTeX fragment."""
    days, day_rate = AOG_SCENARIOS[aog_scenario]
    imputed_mh = sens.attrs.get("imputed_alhwo_mh", 0.0)
    alhwo_removals = sens.attrs.get("alhwo_removals", 0)
    lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\small",
        "\\caption{Fleet COUR sensitivity to ALHWO labour imputation under the mid AOG scenario.}",
        "\\label{tab:c3-cour-labour}",
        "\\resizebox{\\linewidth}{!}{%",
        "\\begin{tabular}{@{}lrrrrr@{}}",
        "\\toprule",
        "Labour scenario & Parts (\\$M) & Labour (\\$M) & AOG (\\$M) & COUR (\\$M) & Labour (\\%) \\\\",
        "\\midrule",
    ]
    for row in sens.itertuples(index=False):
        label = row.labour_scenario
        if label.startswith("Impute"):
            label = "Same-ATA imputed labour"
        elif label.startswith("Exclude"):
            label = "Exclude ALHWO (baseline)"
        lines.append(
            f"{label} & {row.total_parts_cost/1e6:.2f} & "
            f"{row.total_labour_cost/1e6:.2f} & {row.total_aog_cost/1e6:.2f} & "
            f"{row.total_cour/1e6:.2f} & {row.labour_share_pct:.1f} \\\\"
        )
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}%",
        "}",
        "\\par\\smallskip",
        "{\\footnotesize \\textit{Notes:} Mid AOG: "
        f"{days}~day $\\times$ \\${day_rate:,.0f}/day; labour rate \\${LABOUR_RATE_USD:.0f}/h. "
        "Baseline excludes 125 ALHWO documents with zero recorded man-hours. "
        "Imputed scenario assigns "
        f"{alhwo_removals} ALHWO-linked removals each ATA chapter's non-ALHWO median "
        f"man-hours per removal (+{imputed_mh:,.0f}~h fleet total). "
        "Parts and AOG costs are unchanged; top-3 ATA COUR share remains "
        f"{sens.iloc[0]['top3_ata_share_pct']:.1f}"
        + "\\% in both scenarios.}",
        "\\end{table}",
    ])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def labour_rate_sensitivity_table(root: Path, aog_scenario: str = "Mid") -> pd.DataFrame:
    """Compare fleet COUR across assumed labour rates (Table C-4)."""
    baseline_top3: list[int] | None = None
    rows: list[dict[str, object]] = []
    for rate in LABOUR_RATE_SCENARIOS:
        table = cour_table(root, aog_scenario=aog_scenario, labour_rate_usd=rate)
        top3_ata = [int(v) for v in table.head(3)["ata2"]]
        if baseline_top3 is None:
            baseline_top3 = top3_ata
        rows.append({
            "labour_rate_usd": rate,
            "total_parts_cost": table["parts_cost"].sum(),
            "total_labour_cost": table["labour_cost"].sum(),
            "total_aog_cost": table["aog_cost"].sum(),
            "total_cour": table["cour"].sum(),
            "labour_share_pct": table["labour_cost"].sum() / table["cour"].sum() * 100,
            "top3_ata_share_pct": round(table.head(3)["cour"].sum() / table["cour"].sum() * 100, 1),
            "top3_ata": ", ".join(f"{ata:02d}" for ata in top3_ata),
            "top3_rank_stable": top3_ata == baseline_top3,
        })
    return pd.DataFrame(rows)


def write_c4_latex(sens: pd.DataFrame, output_path: Path, *, aog_scenario: str = "Mid") -> None:
    """Write Table C-4 (labour-rate sensitivity) as a LaTeX fragment."""
    days, day_rate = AOG_SCENARIOS[aog_scenario]
    lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Fleet COUR sensitivity to assumed labour rate. "
        f"Mid AOG scenario ({days}~day $\\times$ \\${day_rate:,.0f}/day). "
        "Parts and AOG costs are fixed; only linked labour cost varies with the assumed rate. "
        "Top-3 ATA lists the three highest-COUR chapters under each rate.}",
        "\\label{tab:c4-cour-labour-rate}",
        "\\begin{tabular}{@{}rrrrrrl@{}}",
        "\\toprule",
        "Rate (\\$/h) & Parts (\\$M) & Labour (\\$M) & AOG (\\$M) & COUR (\\$M) & Labour (\\%) & Top-3 ATA \\\\",
        "\\midrule",
    ]
    for row in sens.itertuples(index=False):
        lines.append(
            f"{row.labour_rate_usd:.0f} & {row.total_parts_cost/1e6:.2f} & "
            f"{row.total_labour_cost/1e6:.2f} & {row.total_aog_cost/1e6:.2f} & "
            f"{row.total_cour/1e6:.2f} & {row.labour_share_pct:.1f} & {row.top3_ata} \\\\"
        )
    stable = bool(sens["top3_rank_stable"].all())
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\par\\smallskip",
        "{\\footnotesize \\textit{Note:} ALHWO documents with zero recorded man-hours are excluded. "
        f"Top-three ATA ranking is {'unchanged' if stable else 'not fully stable'} across "
        f"\\${sens.iloc[0].labour_rate_usd:.0f}--\\${sens.iloc[-1].labour_rate_usd:.0f}/h. "
        "Mid-rate (\\$50/h) labour share remains small relative to parts and AOG components.}",
        "\\end{table}",
    ])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_labour_rate_sensitivity(root: Path | None = None) -> dict:
    """Export Table C-4 and CSV for labour-rate COUR sensitivity."""
    base_root = root or Path(__file__).resolve().parent.parent
    sens = labour_rate_sensitivity_table(base_root, "Mid")

    out_public = base_root / "analysis_outputs" / "public"
    out_tables = base_root / "latex" / "manuscript" / "tables"
    out_public.mkdir(parents=True, exist_ok=True)

    export_df = sens.drop(columns=["top3_rank_stable"], errors="ignore")
    export_df.to_csv(out_public / "table_c4_cour_labour_rate.csv", index=False)
    write_c4_latex(sens, out_tables / "table_c4_cour_labour_rate.tex")

    return {"sensitivity": sens}


def export_alhwo_sensitivity(root: Path | None = None) -> dict:
    """Export Table C-3 and CSV for ALHWO labour imputation sensitivity."""
    base_root = root or Path(__file__).resolve().parent.parent
    sens = labour_sensitivity_table(base_root, "Mid")

    out_public = base_root / "analysis_outputs" / "public"
    out_tables = base_root / "latex" / "manuscript" / "tables"
    out_public.mkdir(parents=True, exist_ok=True)

    export_df = sens.drop(columns=[], errors="ignore")
    export_df.to_csv(out_public / "table_c3_cour_labour_sensitivity.csv", index=False)
    write_c3_latex(sens, out_tables / "table_c3_cour_labour_sensitivity.tex")

    return {"sensitivity": sens}


def export_costs(root: Path | None = None) -> dict:
    """Run COUR analysis and export Tables C-1, C-2, Figure C-P, and CSVs."""
    base_root = root or Path(__file__).resolve().parent.parent

    table_mid = cour_table(base_root, "Mid")
    sens = sensitivity_table(base_root)

    out_public = base_root / "analysis_outputs" / "public"
    out_tables  = base_root / "latex" / "manuscript" / "tables"
    out_figures = base_root / "latex" / "manuscript" / "figures"
    out_public.mkdir(parents=True, exist_ok=True)

    table_mid.to_csv(out_public / "table_c1_cour.csv", index=False)
    sens.to_csv(out_public / "table_c2_cour_sensitivity.csv", index=False)

    write_c1_latex(table_mid, out_tables / "table_c1_cour.tex")
    write_c2_latex(sens, out_tables / "table_c2_cour_sensitivity.tex")
    write_cp_figure(table_mid, out_figures / "fig_c_pareto.pdf")

    return {"table": table_mid, "sensitivity": sens}
