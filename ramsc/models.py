"""Data models for the RAMSC analytics framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Base:
    """Operating base for METRIC availability modelling."""

    id: int
    name: str
    dtrans: float
    assets: int
    duty_cycle: float
    grounded: float
    dtrans_std: float = 0.0


@dataclass
class Part:
    """Repairable spare part for METRIC pipeline and stock optimisation."""

    name: str
    cost: float
    lambda_: float
    qpa: int
    drt: float
    bdr: List[float] = field(default_factory=list)
    drt_std: float = 0.0


@dataclass
class PartStockResult:
    """Stock policy outcome for a single part."""

    name: str
    stock: int
    ebo: float
    fill_rate: float
    pipeline: float
    demand_rate: float


@dataclass
class MetricSolution:
    """Full METRIC optimisation result for one base."""

    base_name: str
    parts: List[PartStockResult]
    total_cost: float
    operational_availability: float
    grounded_cost: float
    waiting_time_hours: float
    adjusted_waiting_time_hours: float
    system_mtbf_hours: float
    sum_ebo: float
    trajectory_costs: List[float] = field(default_factory=list)
    trajectory_ao: List[float] = field(default_factory=list)
    trajectory_fill_rate: List[float] = field(default_factory=list)
