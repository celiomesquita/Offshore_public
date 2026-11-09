"""Maintainability analysis for the RAMSC Results section (Step 3 / Table M-1)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ramsc.panel import filter_tracked_unscheduled_mechanical, load_raw_datasets, repo_data_paths

ATA2_LABELS: dict[int, str] = {
    21: "Air conditioning",
    22: "Auto flight",
    24: "Electrical power",
    25: "Equipment / furnishings",
    29: "Hydraulic power",
    31: "Indicating / recording",
    32: "Landing gear",
    34: "Navigation",
    53: "Fuselage",
    55: "Stabilisers",
    62: "Rotors",
    63: "Rotor drive",
    64: "Tail rotor",
    65: "Tail rotor drive",
    71: "Powerplant",
}


def maintainability_table(
    root: Path | None = None,
    *,
    impute_alhwo: bool = False,
) -> tuple[pd.DataFrame, dict]:
    """Compute ATA-level maintainability burden table (Table M-1).

    Man-hours are proportionally allocated to ATA systems for documents that
    span multiple ATA chapters (5 % of documents); each document's man-hours
    are split in proportion to its removal count per ATA.

    Returns
    -------
    table : pd.DataFrame
        ATA-level maintainability summary, sorted by total man-hours descending.
    meta : dict
        Scalar statistics for the Results prose (totals, ALHWO counts, etc.).
    """
    paths = repo_data_paths(root)
    _, removals, tasks = load_raw_datasets(root)

    tracked = filter_tracked_unscheduled_mechanical(removals)
    tracked = tracked.copy()
    tracked["ata2"] = (pd.to_numeric(tracked["ATA #"], errors="coerce") // 100).astype("Int64")

    doc_link_path = (root or paths["hours"].parent.parent) / "analysis_outputs" / "doc_task_removal_link.csv"
    doc = pd.read_csv(doc_link_path)

    merged = tracked.merge(doc[["Source Doc #", "manhours", "nst_tasks"]], on="Source Doc #", how="left")

    alhwo_mask = merged["Source Doc #"].astype(str).str.startswith("ALHWO")
    alhwo_by_ata = (
        merged[alhwo_mask]
        .groupby("ata2")["Source Doc #"]
        .nunique()
        .rename("alhwo_docs")
    )
    alhwo_total_docs = int(merged.loc[alhwo_mask, "Source Doc #"].nunique())
    alhwo_total_removals = int(alhwo_mask.sum())

    non_alhwo = merged[~alhwo_mask].copy()

    # Proportional man-hour allocation across ATAs per document.
    doc_ata = non_alhwo.groupby(["Source Doc #", "ata2"]).size().rename("rem_count").reset_index()
    doc_total = doc_ata.groupby("Source Doc #")["rem_count"].sum().rename("total_rem")
    doc_ata = doc_ata.join(doc_total, on="Source Doc #")
    doc_ata["frac"] = doc_ata["rem_count"] / doc_ata["total_rem"]

    doc_mh = non_alhwo[["Source Doc #", "manhours", "nst_tasks"]].drop_duplicates("Source Doc #")
    doc_ata = doc_ata.merge(doc_mh, on="Source Doc #")
    doc_ata["mh_alloc"] = doc_ata["manhours"] * doc_ata["frac"]
    doc_ata["nst_alloc"] = doc_ata["nst_tasks"] * doc_ata["frac"]

    table = (
        doc_ata.groupby("ata2")
        .agg(
            total_manhours=("mh_alloc", "sum"),
            linked_work_orders=("Source Doc #", "nunique"),
            removals_linked=("rem_count", "sum"),
            nst_tasks=("nst_alloc", "sum"),
        )
        .reset_index()
    )
    table = table.join(alhwo_by_ata, on="ata2").fillna({"alhwo_docs": 0})
    table["alhwo_docs"] = table["alhwo_docs"].astype(int)

    alhwo_removals = (
        merged.loc[alhwo_mask]
        .groupby("ata2")
        .size()
        .rename("alhwo_removals")
        .reset_index()
    )
    table = table.merge(alhwo_removals, on="ata2", how="left")
    table["alhwo_removals"] = table["alhwo_removals"].fillna(0).astype(int)

    table["manhours_per_removal"] = table["total_manhours"] / table["removals_linked"]
    fleet_median_mh_per_rem = float(table.loc[table["removals_linked"] > 0, "manhours_per_removal"].median())

    if impute_alhwo:
        mh_rate_map = table.set_index("ata2")["manhours_per_removal"].to_dict()
        table["imputed_alhwo_mh"] = table.apply(
            lambda row: row["alhwo_removals"]
            * mh_rate_map.get(row["ata2"], fleet_median_mh_per_rem),
            axis=1,
        )
        table["total_manhours"] = table["total_manhours"] + table["imputed_alhwo_mh"]
        table["manhours_per_removal"] = table["total_manhours"] / (
            table["removals_linked"] + table["alhwo_removals"]
        ).replace(0, pd.NA)
    else:
        table["imputed_alhwo_mh"] = 0.0

    table["ata_label"] = table["ata2"].map(lambda c: ATA2_LABELS.get(int(c), "Other"))
    table = table.sort_values("total_manhours", ascending=False).reset_index(drop=True)

    multi_ata_docs = int((non_alhwo.groupby("Source Doc #")["ata2"].nunique() > 1).sum())
    total_non_alhwo_docs = int(non_alhwo["Source Doc #"].nunique())

    meta = {
        "total_manhours": round(float(table["total_manhours"].sum()), 2),
        "imputed_alhwo_mh": round(float(table["imputed_alhwo_mh"].sum()), 2),
        "impute_alhwo": impute_alhwo,
        "fleet_median_mh_per_rem": round(fleet_median_mh_per_rem, 2),
        "total_linked_work_orders": int(table["linked_work_orders"].sum()),
        "alhwo_total_docs": alhwo_total_docs,
        "alhwo_total_removals": alhwo_total_removals,
        "multi_ata_docs": multi_ata_docs,
        "total_non_alhwo_docs": total_non_alhwo_docs,
        "multi_ata_pct": round(multi_ata_docs / total_non_alhwo_docs * 100, 1),
        "top_ata": int(table.iloc[0]["ata2"]),
        "top_ata_label": table.iloc[0]["ata_label"],
        "top_ata_manhours": round(float(table.iloc[0]["total_manhours"]), 1),
        "top_ata_share_pct": round(float(table.iloc[0]["total_manhours"]) / float(table["total_manhours"].sum()) * 100, 1),
        "top_ata_mh_per_removal": round(float(table.iloc[0]["manhours_per_removal"]), 1),
    }
    return table, meta


def write_m1_latex(table: pd.DataFrame, meta: dict, output_path: Path) -> None:
    """Write Results Table M-1 as a LaTeX tabular fragment."""
    lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Corrective maintenance burden by ATA system. "
        "Man-hours are proportionally allocated to ATA chapters for the "
        + str(meta["multi_ata_pct"])
        + "\\% of work orders spanning more than one ATA system. "
        "ALHWO work orders carry zero recorded man-hours and are counted separately.}",
        "\\label{tab:m1-maintainability}",
        "\\resizebox{\\linewidth}{!}{%",
        "\\begin{tabular}{@{}rlrrrrrr@{}}",
        "\\toprule",
        "Rank & ATA (system) & WOs & ALHWO & Removals & Man-h & h/rem. & NST \\\\",
        "\\midrule",
    ]
    for rank, row in enumerate(table.head(10).itertuples(index=False), start=1):
        lines.append(
            f"{rank} & {int(row.ata2):02d} ({row.ata_label}) & "
            f"{int(row.linked_work_orders)} & {int(row.alhwo_docs)} & "
            f"{int(row.removals_linked)} & {row.total_manhours:,.0f} & "
            f"{row.manhours_per_removal:.1f} & {row.nst_tasks:.0f} \\\\"
        )
    lines.extend([
        "\\midrule",
        f"\\multicolumn{{2}}{{l}}{{Fleet total (all ATA)}} & "
        f"{meta['total_linked_work_orders']} & {meta['alhwo_total_docs']} & "
        f"--- & {meta['total_manhours']:,.0f} & --- & --- \\\\",
        "\\bottomrule",
        "\\end{tabular}%",
        "}",
        "\\par\\smallskip",
        "{\\footnotesize \\textit{Notes:} WOs = non-ALHWO ALTL execution documents "
        "linked to tracked unscheduled mechanical removals. "
        "ALHWO = work-order class with zero recorded man-hours; "
        f"total {meta['alhwo_total_docs']} ALHWO documents ({meta['alhwo_total_removals']} removals) "
        "are excluded from man-hour totals. "
        "Man-h = total man-hours; h/rem.\\ = man-hours per removal; "
        "NST = non-scheduled tasks allocated from linked work orders.}",
        "\\end{table}",
    ])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_maintainability(
    root: Path | None = None,
    *,
    table_tex: Path | None = None,
    csv_path: Path | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Export Table M-1 LaTeX file and anonymised CSV."""
    base = root or Path(__file__).resolve().parent.parent
    table, meta = maintainability_table(base)

    if csv_path is None:
        csv_path = base / "analysis_outputs" / "public" / "table_m1_maintainability.csv"
    if table_tex is None:
        table_tex = base / "latex" / "manuscript" / "tables" / "table_m1_maintainability.tex"

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(csv_path, index=False)
    write_m1_latex(table, meta, table_tex)
    return table, meta
