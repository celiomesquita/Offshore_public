"""Reliability Pareto tables and figures for the Results section."""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from ramsc.costs import AOG_SCENARIOS, LABOUR_RATE_USD
from ramsc.panel import (
    filter_tracked_unscheduled_mechanical,
    load_raw_datasets,
    repo_data_paths,
)

# Common ATA chapter labels for publication tables (two-digit ATA).
ATA2_LABELS: dict[int, str] = {
    21: "Air conditioning",
    22: "Auto flight",
    24: "Electrical power",
    25: "Equipment / furnishings",
    31: "Indicating / recording",
    32: "Landing gear",
    34: "Navigation",
    62: "Rotor(s)",
    63: "Rotor drive",
    64: "Tail rotor",
}


def ata_pareto_table(
    root: Path | None = None,
    *,
    top_n: int = 10,
) -> pd.DataFrame:
    """Build the top-N ATA Pareto table (Results Table R-1)."""
    paths = repo_data_paths(root)
    hours = pd.read_excel(paths["hours"], sheet_name="Sheet1")
    hours["Hours"] = pd.to_numeric(hours["Hours"], errors="coerce").fillna(0)
    total_hours = float(hours["Hours"].sum())

    _, removals, _ = load_raw_datasets(root)
    tracked = filter_tracked_unscheduled_mechanical(removals)
    tracked["ata2"] = (pd.to_numeric(tracked["ATA #"], errors="coerce") // 100).astype(int)

    counts = (
        tracked.groupby("ata2")
        .size()
        .rename("removals")
        .sort_values(ascending=False)
        .astype(int)
    )
    table = counts.to_frame()
    table["share_pct"] = table["removals"] / table["removals"].sum() * 100
    table["cum_share_pct"] = table["share_pct"].cumsum()
    table["rate_1000h"] = table["removals"] / total_hours * 1000
    table["ata_label"] = table.index.map(lambda code: ATA2_LABELS.get(code, "Other"))
    table = table.reset_index().rename(columns={"ata2": "ata2"})
    return table.head(top_n)


def write_r1_latex(table: pd.DataFrame, output_path: Path) -> None:
    """Write Results Table R-1 as a LaTeX tabular fragment."""
    lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Top ATA systems by tracked unscheduled mechanical removal count (R-1).}",
        "\\label{tab:r1-ata-pareto}",
        "\\resizebox{0.8\\linewidth}{!}{%",
        "\\setlength{\\tabcolsep}{5pt}",
        "\\begin{tabular}{@{}rlrrr@{}}",
        "\\toprule",
        "Rank & ATA & Removals & Rate (per 1{,}000 h) & Cum.\\ share (\\%) \\\\",
        "\\midrule",
    ]
    for rank, row in enumerate(table.itertuples(index=False), start=1):
        lines.append(
            f"{rank} & {int(row.ata2):02d} ({row.ata_label}) & {int(row.removals)} & "
            f"{row.rate_1000h:.2f} & {row.cum_share_pct:.1f} \\\\"
        )
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}%",
            "}",
            "\\par\\smallskip",
            "{\\footnotesize \\textit{Note:} Rate normalised by total fleet exposure "
            "(33{,}486.6 flight hours). Life-vest and other regulated safety-equipment "
            "removals are excluded.}",
            "\\end{table}",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_pareto_figure(
    table: pd.DataFrame,
    output_path: Path,
    *,
    total_hours: float = 33_486.6,
) -> None:
    """Write the ATA Pareto chart (Figure R-P)."""
    plot_data = table.sort_values("removals", ascending=True)
    ata_labels = [f"{int(code):02d}" for code in plot_data["ata2"]]

    fig, ax1 = plt.subplots(figsize=(7.0, 4.5))
    bars = ax1.barh(
        ata_labels,
        plot_data["removals"],
        color="#4C72B0",
        edgecolor="white",
        linewidth=0.6,
    )
    ax1.set_xlabel("Tracked unscheduled removals")
    ax1.set_ylabel("ATA chapter")
    ax1.set_title("ATA-level Pareto distribution of unscheduled removals")

    ax2 = ax1.twiny()
    ax2.plot(
        plot_data["cum_share_pct"],
        ata_labels,
        color="#C44E52",
        marker="o",
        linewidth=1.8,
        markersize=5,
        label="Cumulative share",
    )
    ax2.set_xlabel("Cumulative share (%)")
    ax2.set_xlim(0, 100)
    ax2.grid(False)

    for bar, rate in zip(bars, plot_data["rate_1000h"], strict=True):
        ax1.text(
            bar.get_width() + 4,
            bar.get_y() + bar.get_height() / 2,
            f"{rate:.1f}/1k h",
            va="center",
            ha="left",
            fontsize=8,
            color="#333333",
        )

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def _latex_text(text: str) -> str:
    """Escape plain text for LaTeX tabular cells."""
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "_": r"\_",
        "#": r"\#",
        "$": r"\$",
    }
    result = text
    for key, value in replacements.items():
        result = result.replace(key, value)
    return result


def _short_description(description: str, max_len: int = 38) -> str:
    """Normalize part description for publication tables."""
    cleaned = re.sub(r"\s+", " ", str(description)).strip().lower()
    if not cleaned:
        return cleaned
    replacements = {
        "assy": "assembly",
        "pre bt139": "pre-BT139",
        "post bt139": "post-BT139",
        " tr": " TR",
    }
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    if len(cleaned) > max_len:
        candidate = cleaned[: max_len - 3].rsplit(" ", 1)[0]
        if len(candidate) < max_len // 2:
            candidate = cleaned[: max_len - 3]
        text = candidate.rstrip("(-/,;:")
        text = f"{text}..."
    else:
        text = cleaned
    return text[0].upper() + text[1:]


def _latex_part(part_number: str) -> str:
    return f"\\texttt{{{part_number}}}"


def _aog_cost_per_event(scenario: str) -> float:
    days, day_rate = AOG_SCENARIOS[scenario]
    return days * day_rate


def _part_labour_costs(tracked: pd.DataFrame, root: Path) -> pd.Series:
    """Allocate linked work-order man-hours to part numbers (non-ALHWO only)."""
    doc_link_path = root / "analysis_outputs" / "doc_task_removal_link.csv"
    if not doc_link_path.exists():
        return pd.Series(dtype=float)

    doc = pd.read_csv(doc_link_path)
    merged = tracked.merge(doc[["Source Doc #", "manhours"]], on="Source Doc #", how="left")
    alhwo_mask = merged["Source Doc #"].astype(str).str.startswith("ALHWO")
    non_alhwo = merged.loc[~alhwo_mask].copy()
    if non_alhwo.empty:
        return pd.Series(dtype=float)

    doc_part = (
        non_alhwo.groupby(["Source Doc #", "Part #"], as_index=False)
        .size()
        .rename(columns={"size": "part_count"})
    )
    doc_total = doc_part.groupby("Source Doc #")["part_count"].sum().rename("doc_total")
    doc_part = doc_part.join(doc_total, on="Source Doc #")
    doc_part["frac"] = doc_part["part_count"] / doc_part["doc_total"]

    doc_mh = non_alhwo[["Source Doc #", "manhours"]].drop_duplicates("Source Doc #")
    doc_part = doc_part.merge(doc_mh, on="Source Doc #")
    doc_part["mh_alloc"] = pd.to_numeric(doc_part["manhours"], errors="coerce").fillna(0) * doc_part["frac"]

    labour_hours = doc_part.groupby("Part #")["mh_alloc"].sum()
    return labour_hours * LABOUR_RATE_USD


def component_pareto_table(
    root: Path | None = None,
    *,
    top_n: int = 10,
    aog_scenario: str = "Mid",
) -> pd.DataFrame:
    """Build top-N component Pareto table with COUR and rank divergence (Table R-2)."""
    base = root or Path(__file__).resolve().parent.parent
    paths = repo_data_paths(base)
    hours = pd.read_excel(paths["hours"], sheet_name="Sheet1")
    hours["Hours"] = pd.to_numeric(hours["Hours"], errors="coerce").fillna(0)
    total_hours = float(hours["Hours"].sum())

    _, removals, _ = load_raw_datasets(base)
    tracked = filter_tracked_unscheduled_mechanical(removals).copy()
    tracked["Std Cost"] = pd.to_numeric(tracked["Std Cost"], errors="coerce").fillna(0)
    tracked["ata2"] = (pd.to_numeric(tracked["ATA #"], errors="coerce") // 100).astype(int)

    table = (
        tracked.groupby(["Part #", "Part Description"], as_index=False)
        .agg(
            removals=("Part #", "size"),
            ata2=("ata2", "first"),
            parts_cost=("Std Cost", "sum"),
        )
        .sort_values("removals", ascending=False)
    )
    table["rate_1000h"] = table["removals"] / total_hours * 1000
    table["share_pct"] = table["removals"] / table["removals"].sum() * 100
    table["cum_share_pct"] = table["share_pct"].cumsum()

    labour = _part_labour_costs(tracked, base)
    table["labour_cost"] = table["Part #"].map(labour).fillna(0)
    aog_rate = _aog_cost_per_event(aog_scenario)
    table["aog_cost"] = table["removals"] * aog_rate
    table["cour"] = table["parts_cost"] + table["labour_cost"] + table["aog_cost"]

    table = table.sort_values("removals", ascending=False).reset_index(drop=True)
    table["vol_rank"] = table.index + 1
    cour_order = table.sort_values("cour", ascending=False).reset_index(drop=True)
    cour_rank_map = {row["Part #"]: i + 1 for i, row in cour_order.iterrows()}
    table["cour_rank"] = table["Part #"].map(cour_rank_map)
    table["rank_diff"] = table["vol_rank"] - table["cour_rank"]
    table["description_short"] = table["Part Description"].map(_short_description)

    return table.head(top_n)


def write_r2_latex(table: pd.DataFrame, output_path: Path, *, aog_scenario: str = "Mid") -> None:
    """Write Results Table R-2 as a LaTeX tabular fragment."""
    days, day_rate = AOG_SCENARIOS[aog_scenario]
    lines = [
        "\\begin{table}[!htbp]",
        "\\centering",
        "\\caption{Top components by tracked unscheduled mechanical removal count and COUR "
        f"({aog_scenario} AOG scenario). "
        f"Labour: \\${LABOUR_RATE_USD:.0f}/h from linked work orders; "
        f"AOG: {days}~day $\\times$ \\${day_rate:,.0f}/day per removal event. "
        "Volume rank (Vol.\\ rk) and COUR rank divergence ($\\Delta$rk) highlight parts "
        "whose economic priority differs from removal frequency.}",
        "\\label{tab:r2-component-pareto}",
        "{\\footnotesize",
        "\\setlength{\\tabcolsep}{3pt}",
        "\\renewcommand{\\arraystretch}{1.15}",
        "\\begin{tabularx}{\\linewidth}{@{}"
        ">{\\centering\\arraybackslash}p{0.45cm}"
        ">{\\raggedright\\arraybackslash}p{2.35cm}"
        ">{\\raggedright\\arraybackslash}X"
        ">{\\centering\\arraybackslash}p{0.55cm}"
        ">{\\centering\\arraybackslash}p{0.85cm}"
        ">{\\centering\\arraybackslash}p{0.85cm}"
        ">{\\centering\\arraybackslash}p{0.85cm}"
        ">{\\centering\\arraybackslash}p{0.55cm}"
        ">{\\centering\\arraybackslash}p{0.55cm}"
        ">{\\centering\\arraybackslash}p{0.55cm}@{}}",
        "\\toprule",
        "Rk & Part & Description & Rem. & Rate & Parts & COUR & Vol. & COUR & $\\Delta$ \\\\",
        " & & & & (/1k h) & (\\$k) & (\\$k) & rk & rk & rk \\\\",
        "\\midrule",
    ]
    for rank, (_, row) in enumerate(table.iterrows(), start=1):
        delta = int(row["rank_diff"])
        delta_str = f"+{delta}" if delta > 0 else str(delta)
        desc = _latex_text(row["description_short"])
        lines.append(
            f"{rank} & {_latex_part(row['Part #'])} & {desc} & "
            f"{int(row['removals'])} & {row['rate_1000h']:.2f} & {row['parts_cost'] / 1000:.1f} & "
            f"{row['cour'] / 1000:.1f} & {int(row['vol_rank'])} & {int(row['cour_rank'])} & {delta_str} \\\\"
        )
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabularx}",
            "}",
            "\\par\\smallskip",
            "{\\footnotesize \\textit{Notes:} Rem.\\ = tracked unscheduled mechanical removals. "
            "Rate normalised by total fleet exposure (33{,}486.6 flight hours). "
            "ALHWO work orders excluded from labour. "
            "Positive $\\Delta$rk: COUR priority exceeds volume priority.}",
            "\\end{table}",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_component_pareto(
    root: Path | None = None,
    *,
    table_tex: Path | None = None,
    csv_path: Path | None = None,
    top_n: int = 10,
    aog_scenario: str = "Mid",
) -> pd.DataFrame:
    """Export Table R-2 and an anonymised CSV summary."""
    base = root or Path(__file__).resolve().parent.parent
    full = component_pareto_table(base, top_n=10_000, aog_scenario=aog_scenario)
    table = full.head(top_n).copy()

    if csv_path is None:
        csv_path = base / "analysis_outputs" / "public" / "table_r2_component_pareto.csv"
    if table_tex is None:
        table_tex = base / "latex" / "manuscript" / "tables" / "table_r2_component_pareto.tex"

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(csv_path, index=False)
    write_r2_latex(table, table_tex, aog_scenario=aog_scenario)
    return table


def export_reliability_pareto(
    root: Path | None = None,
    *,
    table_tex: Path | None = None,
    figure_path: Path | None = None,
    csv_path: Path | None = None,
    top_n: int = 10,
) -> pd.DataFrame:
    """Export Table R-1, Figure R-P, and an anonymised CSV summary."""
    base = root or Path(__file__).resolve().parent.parent
    table = ata_pareto_table(base, top_n=top_n)

    if csv_path is None:
        csv_path = base / "analysis_outputs" / "public" / "table_r1_ata_pareto.csv"
    if table_tex is None:
        table_tex = base / "latex" / "manuscript" / "tables" / "table_r1_ata_pareto.tex"
    if figure_path is None:
        figure_path = base / "latex" / "manuscript" / "figures" / "fig_r_pareto_ata.pdf"

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(csv_path, index=False)
    write_r1_latex(table, table_tex)
    write_pareto_figure(table, figure_path)
    return table
