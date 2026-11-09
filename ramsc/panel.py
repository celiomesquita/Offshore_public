"""Aircraft × ATA × month panel construction for RAMSC models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from ramsc.anonymize import anonymize_aircraft_column, load_aircraft_id_map
from ramsc.constants import LOCAL_TASKS_FILENAME, NST_SYSTEM_PREFIX

ALHWO_DOC_PREFIX = "ALHWO"
LOW_EXPOSURE_HOURS = 500.0


@dataclass(frozen=True)
class PanelBuildSummary:
    """Summary statistics from a panel build run."""

    rows: int
    aircraft: int
    months: int
    ata2_systems: int
    total_flight_hours: float
    total_removals: int
    total_nst_allocated: float
    total_manhours_allocated: float
    alhwo_tasks_excluded: int
    alhwo_manhours_excluded: float
    tasks_without_ata_link: int
    removals_excluded_no_aircraft: int
    removals_on_zero_hour_months: int
    low_exposure_aircraft: tuple[str, ...]
    is_balanced: bool
    aircraft_month_cells: int
    expected_balanced_rows: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "rows": self.rows,
            "aircraft": self.aircraft,
            "months": self.months,
            "ata2_systems": self.ata2_systems,
            "total_flight_hours": self.total_flight_hours,
            "total_removals": self.total_removals,
            "total_nst_allocated": self.total_nst_allocated,
            "total_manhours_allocated": self.total_manhours_allocated,
            "alhwo_tasks_excluded": self.alhwo_tasks_excluded,
            "alhwo_manhours_excluded": self.alhwo_manhours_excluded,
            "tasks_without_ata_link": self.tasks_without_ata_link,
            "removals_excluded_no_aircraft": self.removals_excluded_no_aircraft,
            "removals_on_zero_hour_months": self.removals_on_zero_hour_months,
            "low_exposure_aircraft": list(self.low_exposure_aircraft),
            "is_balanced": self.is_balanced,
            "aircraft_month_cells": self.aircraft_month_cells,
            "expected_balanced_rows": self.expected_balanced_rows,
        }


def repo_data_paths(root: Path | None = None) -> dict[str, Path]:
    """Return default paths to the three operator Excel exports."""
    base = root or Path(__file__).resolve().parent.parent
    return {
        "hours": base / "data" / "hours_flown.xlsx",
        "removals": base / "data" / "removals.xlsx",
        "tasks": base / "data" / LOCAL_TASKS_FILENAME,
    }


def month_key(series: pd.Series) -> pd.Series:
    """Convert datetimes to YYYY-MM strings."""
    return pd.to_datetime(series, dayfirst=True, errors="coerce").dt.to_period("M").astype("string")


def ata2_series(ata: pd.Series) -> pd.Series:
    """Extract two-digit ATA chapter codes from four-digit ATA values."""
    return (pd.to_numeric(ata, errors="coerce") // 100).astype("Int64")


def load_raw_datasets(
    root: Path | None = None,
    *,
    hours_path: Path | None = None,
    removals_path: Path | None = None,
    tasks_path: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load and normalise the three source datasets."""
    defaults = repo_data_paths(root)
    hours = pd.read_excel(hours_path or defaults["hours"], sheet_name="Sheet1")
    removals = pd.read_excel(removals_path or defaults["removals"], sheet_name="Sheet1")
    tasks = pd.read_excel(tasks_path or defaults["tasks"], sheet_name="Sheet1")

    hours["Flight Date"] = pd.to_datetime(hours["Flight Date"], dayfirst=True, errors="coerce")
    removals["Removed Date_dt"] = pd.to_datetime(
        removals["Removed Date"], dayfirst=True, errors="coerce"
    )
    tasks["Tech Sign Off Date_dt"] = pd.to_datetime(
        tasks["Tech Sign Off Date"], format="%m/%d/%Y", errors="coerce"
    )

    for col in ("Hours", "Take Off", "Starts"):
        hours[col] = pd.to_numeric(hours[col], errors="coerce").fillna(0)
    tasks["Tot Man Hours"] = pd.to_numeric(tasks["Tot Man Hours"], errors="coerce").fillna(0)

    return hours, removals, tasks


def filter_tracked_unscheduled_mechanical(removals: pd.DataFrame) -> pd.DataFrame:
    """Return tracked unscheduled discrepancy removals excluding life-vest equipment."""
    tracked = removals[
        removals["Reason Category"].astype(str).str.upper().eq("UNSCHEDULED")
        & removals["Reason Code"].astype(str).str.upper().eq("DISCREPANCY")
        & removals["Removal Type"].astype(str).str.upper().eq("TRACKED")
    ].copy()
    life_vest_mask = tracked["Part Description"].astype(str).str.upper().str.contains(
        "LIFE VEST|LIFE JACKET", na=False
    )
    return tracked.loc[~life_vest_mask].copy()


def _doc_ata_weights(tracked_mech: pd.DataFrame) -> pd.DataFrame:
    """Removal-count weights linking work-order documents to ATA-2 chapters."""
    linked = tracked_mech.dropna(subset=["Source Doc #"]).copy()
    linked["doc"] = linked["Source Doc #"].astype(str)
    linked["ata2"] = ata2_series(linked["ATA #"])
    linked = linked.dropna(subset=["ata2"])
    counts = (
        linked.groupby(["doc", "ata2"], as_index=False)
        .size()
        .rename(columns={"size": "removal_count"})
    )
    totals = counts.groupby("doc")["removal_count"].transform("sum")
    counts["weight"] = counts["removal_count"] / totals
    return counts[["doc", "ata2", "weight"]]


def _aggregate_hours(hours: pd.DataFrame) -> pd.DataFrame:
    frame = hours.copy()
    frame["aircraft"] = frame["Aircraft #"]
    frame = frame.dropna(subset=["aircraft"])
    frame["aircraft"] = frame["aircraft"].astype(str)
    frame["month"] = month_key(frame["Flight Date"])
    frame = frame.dropna(subset=["month"])
    return (
        frame.groupby(["aircraft", "month"], as_index=False)
        .agg(
            H_im=("Hours", "sum"),
            takeoffs_im=("Take Off", "sum"),
            starts_im=("Starts", "sum"),
        )
    )


def _aggregate_removals(tracked_mech: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    frame = tracked_mech.copy()
    frame["aircraft"] = frame["Aircraft #"]
    excluded = int(frame["aircraft"].isna().sum())
    frame = frame.dropna(subset=["aircraft"])
    frame["aircraft"] = frame["aircraft"].astype(str)
    frame["month"] = month_key(frame["Removed Date_dt"])
    frame["ata2"] = ata2_series(frame["ATA #"])
    frame = frame.dropna(subset=["month", "ata2"])
    removal_agg = (
        frame.groupby(["aircraft", "month", "ata2"], as_index=False)
        .agg(Y_iam=("Part #", "size"))
    )
    return removal_agg, excluded


def _aggregate_tasks(
    tasks: pd.DataFrame,
    tracked_mech: pd.DataFrame,
) -> tuple[pd.DataFrame, int, float, int]:
    """Allocate task NST counts and man-hours to ATA-2 via linked work-order documents."""
    doc_weights = _doc_ata_weights(tracked_mech)
    linked_docs = set(doc_weights["doc"])

    frame = tasks.copy()
    frame["doc"] = frame["Execution Doc #"].astype(str)
    frame["aircraft"] = frame["Aircraft #"]
    frame = frame.dropna(subset=["aircraft"])
    frame["aircraft"] = frame["aircraft"].astype(str)
    frame["month"] = month_key(frame["Tech Sign Off Date_dt"])
    frame["is_nst"] = frame["Task #"].astype(str).str.startswith(NST_SYSTEM_PREFIX, na=False)

    alhwo_mask = frame["doc"].str.startswith(ALHWO_DOC_PREFIX, na=False)
    alhwo_tasks_excluded = int(alhwo_mask.sum())
    alhwo_manhours_excluded = float(frame.loc[alhwo_mask, "Tot Man Hours"].sum())

    frame = frame.loc[~alhwo_mask].dropna(subset=["month"])
    tasks_without_ata_link = int((~frame["doc"].isin(linked_docs)).sum())

    allocated = frame.merge(doc_weights, on="doc", how="inner")
    allocated["nst_count_iam"] = allocated["is_nst"].astype(float) * allocated["weight"]
    allocated["manhours_iam"] = allocated["Tot Man Hours"] * allocated["weight"]

    task_agg = (
        allocated.groupby(["aircraft", "month", "ata2"], as_index=False)
        .agg(
            nst_count_iam=("nst_count_iam", "sum"),
            manhours_iam=("manhours_iam", "sum"),
        )
    )
    return task_agg, alhwo_tasks_excluded, alhwo_manhours_excluded, tasks_without_ata_link


def _low_exposure_lookup(map_path: Path | None = None) -> dict[str, bool]:
    """Map actual tail numbers to low-exposure flags from the confidential ID map."""
    mapping = load_aircraft_id_map(map_path)
    if "exposure_band" in mapping.columns:
        return dict(
            zip(
                mapping["actual_id"].astype(str),
                mapping["exposure_band"].astype(str).str.lower().eq("low"),
            )
        )
    if "total_hours" in mapping.columns:
        return dict(
            zip(
                mapping["actual_id"].astype(str),
                mapping["total_hours"].astype(float).lt(LOW_EXPOSURE_HOURS),
            )
        )
    low_ids = mapping.sort_values("hours_rank").tail(3)["actual_id"].astype(str)
    return {aircraft_id: aircraft_id in set(low_ids) for aircraft_id in mapping["actual_id"].astype(str)}


def build_panel(
    root: Path | None = None,
    *,
    hours_path: Path | None = None,
    removals_path: Path | None = None,
    tasks_path: Path | None = None,
    map_path: Path | None = None,
) -> tuple[pd.DataFrame, PanelBuildSummary]:
    """Build the aircraft × ATA-2 × month panel used by RAMSC models."""
    hours, removals, tasks = load_raw_datasets(
        root,
        hours_path=hours_path,
        removals_path=removals_path,
        tasks_path=tasks_path,
    )
    # The flight-log observation window defines the panel; pre-window tasks
    # remain in raw data but cannot create extra months in this study.
    study_start = hours["Flight Date"].min().to_period("M").start_time
    study_end = (hours["Flight Date"].max().to_period("M") + 1).start_time
    removals = removals.loc[removals["Removed Date_dt"].ge(study_start)
                            & removals["Removed Date_dt"].lt(study_end)].copy()
    tasks = tasks.loc[tasks["Tech Sign Off Date_dt"].ge(study_start)
                      & tasks["Tech Sign Off Date_dt"].lt(study_end)].copy()
    tracked_mech = filter_tracked_unscheduled_mechanical(removals)

    hours_agg = _aggregate_hours(hours)
    removal_agg, removals_excluded_no_aircraft = _aggregate_removals(tracked_mech)
    task_agg, alhwo_tasks_excluded, alhwo_manhours_excluded, tasks_without_ata_link = (
        _aggregate_tasks(tasks, tracked_mech)
    )

    fleet_ata2 = sorted(int(value) for value in removal_agg["ata2"].dropna().unique())
    aircraft_months = (
        pd.concat(
            [
                hours_agg[["aircraft", "month"]],
                removal_agg[["aircraft", "month"]],
                task_agg[["aircraft", "month"]],
            ],
            ignore_index=True,
        )
        .drop_duplicates()
    )
    spine = aircraft_months.merge(
        pd.DataFrame({"ata2": fleet_ata2}),
        how="cross",
    )

    panel = (
        spine.merge(hours_agg, on=["aircraft", "month"], how="left")
        .merge(removal_agg, on=["aircraft", "month", "ata2"], how="left")
        .merge(task_agg, on=["aircraft", "month", "ata2"], how="left")
    )
    panel["H_im"] = panel["H_im"].fillna(0.0)
    panel["takeoffs_im"] = panel["takeoffs_im"].fillna(0.0)
    panel["starts_im"] = panel["starts_im"].fillna(0.0)
    panel["Y_iam"] = panel["Y_iam"].fillna(0).astype(int)
    panel["nst_count_iam"] = panel["nst_count_iam"].fillna(0.0)
    panel["manhours_iam"] = panel["manhours_iam"].fillna(0.0)
    panel["ata2"] = panel["ata2"].astype(int)

    exposure_lookup = _low_exposure_lookup(map_path)
    panel["low_exposure"] = panel["aircraft"].map(exposure_lookup).fillna(False)

    low_exposure_aircraft = tuple(
        sorted(aircraft for aircraft, flag in exposure_lookup.items() if flag)
    )
    aircraft_month_cells = len(aircraft_months)
    expected_balanced_rows = aircraft_month_cells * len(fleet_ata2)
    is_balanced = len(panel) == expected_balanced_rows
    removals_on_zero_hour_months = int(
        panel.loc[(panel["H_im"] == 0) & (panel["Y_iam"] > 0), ["aircraft", "month"]]
        .drop_duplicates()
        .shape[0]
    )

    summary = PanelBuildSummary(
        rows=len(panel),
        aircraft=panel["aircraft"].nunique(),
        months=panel["month"].nunique(),
        ata2_systems=len(fleet_ata2),
        total_flight_hours=float(
            panel.drop_duplicates(["aircraft", "month"])["H_im"].sum()
        ),
        total_removals=int(panel["Y_iam"].sum()),
        total_nst_allocated=float(panel["nst_count_iam"].sum()),
        total_manhours_allocated=float(panel["manhours_iam"].sum()),
        alhwo_tasks_excluded=alhwo_tasks_excluded,
        alhwo_manhours_excluded=alhwo_manhours_excluded,
        tasks_without_ata_link=tasks_without_ata_link,
        removals_excluded_no_aircraft=removals_excluded_no_aircraft,
        removals_on_zero_hour_months=removals_on_zero_hour_months,
        low_exposure_aircraft=low_exposure_aircraft,
        is_balanced=is_balanced,
        aircraft_month_cells=aircraft_month_cells,
        expected_balanced_rows=expected_balanced_rows,
    )

    if summary.total_removals != int(removal_agg["Y_iam"].sum()):
        raise ValueError("Panel removal total does not match aggregated removal counts.")

    return panel, summary


def build_public_panel(
    root: Path | None = None,
    *,
    map_path: Path | None = None,
    **kwargs: Any,
) -> tuple[pd.DataFrame, PanelBuildSummary]:
    """Build the panel and anonymise aircraft identifiers for publication export."""
    panel, summary = build_panel(root, map_path=map_path, **kwargs)
    public = panel.rename(columns={"aircraft": "pt_id"})
    public = anonymize_aircraft_column(public, column="pt_id", map_path=map_path)
    column_order = [
        "pt_id",
        "month",
        "ata2",
        "H_im",
        "Y_iam",
        "takeoffs_im",
        "starts_im",
        "nst_count_iam",
        "manhours_iam",
        "low_exposure",
    ]
    return public[column_order].sort_values(["pt_id", "month", "ata2"]).reset_index(drop=True), summary
