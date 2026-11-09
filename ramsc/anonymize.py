"""Anonymise aircraft tail numbers for publication outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Hashable

import pandas as pd

_CONFIDENTIAL_MAP = Path(__file__).resolve().parent.parent / "config" / "confidential" / "aircraft_id_map.csv"
# The public release ships pseudonymised data (AC-01 ... AC-24) and an identity map with
# exposure bands; the confidential actual-to-public map is never distributed.
_PUBLIC_MAP = Path(__file__).resolve().parent.parent / "config" / "public" / "aircraft_id_map.csv"
DEFAULT_MAP_PATH = _CONFIDENTIAL_MAP if _CONFIDENTIAL_MAP.exists() else _PUBLIC_MAP

AIRCRAFT_COLUMN_CANDIDATES = (
    "Aircraft #",
    "aircraft",
    "Aircraft",
    "aircraft_id",
    "actual_id",
)


def load_aircraft_id_map(map_path: str | Path | None = None) -> pd.DataFrame:
    """Load the confidential actual-to-public aircraft identifier map."""
    path = Path(map_path or DEFAULT_MAP_PATH)
    if not path.exists():
        raise FileNotFoundError(
            f"Aircraft ID map not found at {path}. "
            "Create config/confidential/aircraft_id_map.csv before anonymising."
        )
    mapping = pd.read_csv(path)
    required = {"actual_id", "public_id"}
    if not required.issubset(mapping.columns):
        raise ValueError(f"Map must contain columns: {sorted(required)}")
    return mapping


def aircraft_id_lookup(map_path: str | Path | None = None) -> dict[str, str]:
    """Return a dictionary mapping actual tail numbers to publication IDs."""
    mapping = load_aircraft_id_map(map_path)
    return dict(zip(mapping["actual_id"].astype(str), mapping["public_id"].astype(str)))


def anonymize_aircraft_column(
    frame: pd.DataFrame,
    column: str | None = None,
    *,
    map_path: str | Path | None = None,
    inplace: bool = False,
) -> pd.DataFrame:
    """Replace tail numbers in a DataFrame column with publication IDs."""
    result = frame if inplace else frame.copy()
    lookup = aircraft_id_lookup(map_path)

    target_column = column
    if target_column is None:
        for candidate in AIRCRAFT_COLUMN_CANDIDATES:
            if candidate in result.columns:
                target_column = candidate
                break
    if target_column is None:
        raise ValueError(
            "No aircraft column found. Pass column= explicitly or use one of: "
            + ", ".join(AIRCRAFT_COLUMN_CANDIDATES)
        )

    original = result[target_column].astype(str)
    mapped = original.map(lookup)
    unmapped = mapped.isna()
    if unmapped.any():
        unknown = sorted(original[unmapped].unique())
        raise KeyError(f"Tail numbers missing from map: {unknown}")

    result[target_column] = mapped
    return result


def anonymize_value(tail_number: Hashable, map_path: str | Path | None = None) -> str:
    """Convert one actual tail number to its publication ID."""
    lookup = aircraft_id_lookup(map_path)
    key = str(tail_number)
    if key not in lookup:
        raise KeyError(f"Tail number not in map: {key}")
    return lookup[key]
