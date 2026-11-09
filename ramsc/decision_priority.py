"""MR03 frequency-times-consequence priorities; no safety or availability proxy."""
from __future__ import annotations

import numpy as np
import pandas as pd


def consequence_priority(
    table: pd.DataFrame, *, labour_weight: float,
    labour_reference: float, parts_reference: float,
) -> pd.Series:
    """Return normalised consequence/hour, preserving missing active inputs.

    Inputs: removal_rate (events/hour), labour_per_event (person-hours/event),
    parts_cost_per_event (currency/event). References are fixed positive scales.
    This is an explicit preference scenario, not a validated safety ranking.
    """
    if not np.isfinite(labour_weight) or not 0 <= labour_weight <= 1:
        raise ValueError('labour_weight must be finite and in [0, 1]')
    if any(not np.isfinite(v) or v <= 0 for v in (labour_reference, parts_reference)):
        raise ValueError('reference consequences must be finite and positive')
    active = [('removal_rate', 1.0)]
    if labour_weight > 0:
        active.append(('labour_per_event', labour_weight/labour_reference))
    if labour_weight < 1:
        active.append(('parts_cost_per_event', (1-labour_weight)/parts_reference))
    for column, _ in active:
        values = table[column]
        if ((values < 0) | np.isinf(values)).any():
            raise ValueError(f'{column} must be non-negative, finite or missing')
    consequence = pd.Series(0.0, index=table.index)
    for column, coefficient in active[1:]:
        consequence = consequence + coefficient*table[column]
    return (table.removal_rate*consequence).rename('consequence_priority')
