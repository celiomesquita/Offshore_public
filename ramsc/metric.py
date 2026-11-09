"""METRIC-based spare parts optimisation for the Availability pillar of RAMSC."""

from __future__ import annotations

import math
from typing import List, Literal, Tuple

from scipy.stats import nbinom, poisson

from ramsc.models import Base, MetricSolution, Part, PartStockResult

ConstraintPriority = Literal["budget", "min_fr"]
DemandModel = Literal["poisson", "negbin"]
MAX_STOCK_LEVEL = 169


def calculate_pipeline_and_demand_rate(
    base: Base,
    part_list: List[Part],
    safety_factor: float = 1.0,
) -> Tuple[List[float], List[float]]:
    """Return pipeline demand and hourly demand rate for each part."""
    pipeline: List[float] = []
    demand_rate: List[float] = []

    for part in part_list:
        hourly_demand = (
            float(base.duty_cycle) * float(base.assets) * part.lambda_ * float(part.qpa)
        )
        demand_rate.append(hourly_demand)

        repair_time = part.drt + part.drt_std * safety_factor
        transport_time = base.dtrans + base.dtrans_std * safety_factor
        lead_time_hours = (repair_time + transport_time) * 24.0
        pipeline.append(hourly_demand * lead_time_hours)

    return pipeline, demand_rate


def poisson_pmf(k: int, expected_demand: float) -> float:
    """Poisson probability mass function P(X = k)."""
    return (
        math.exp(-expected_demand)
        * math.pow(expected_demand, float(k))
        / float(math.factorial(k))
    )


def weighted_expected_demand(stock_level: int, expected_demand: float) -> float:
    """Compute sum of k * P(X = k) for k = 0..stock_level."""
    return sum(k * poisson_pmf(k, expected_demand) for k in range(stock_level + 1))


def poisson_cdf(stock_level: int, expected_demand: float) -> float:
    """Pipeline CDF P(X <= stock_level); not immediate service probability."""
    return float(poisson.cdf(stock_level, expected_demand))


def _nb_n_p(expected_demand: float, nb_alpha: float) -> Tuple[float, float]:
    """Map statsmodels-style NB parameters (Var = mu + alpha * mu^2) to scipy n, p."""
    n = 1.0 / nb_alpha
    p = n / (n + expected_demand)
    return n, p


def demand_pmf(
    k: int,
    expected_demand: float,
    *,
    demand_model: DemandModel = "poisson",
    nb_alpha: float = 0.0,
) -> float:
    """Pipeline demand PMF under Poisson or Negative Binomial assumptions."""
    if demand_model == "negbin" and nb_alpha > 0.0:
        n, p = _nb_n_p(expected_demand, nb_alpha)
        return float(nbinom.pmf(k, n, p))
    return poisson_pmf(k, expected_demand)


def demand_cdf(
    stock_level: int,
    expected_demand: float,
    *,
    demand_model: DemandModel = "poisson",
    nb_alpha: float = 0.0,
) -> float:
    """Pipeline CDF P(X <= stock_level)."""
    if demand_model == "negbin" and nb_alpha > 0.0:
        n, p = _nb_n_p(expected_demand, nb_alpha)
        return float(nbinom.cdf(stock_level, n, p))
    return poisson_cdf(stock_level, expected_demand)


def demand_esd(
    stock_level: int,
    expected_demand: float,
    *,
    demand_model: DemandModel = "poisson",
    nb_alpha: float = 0.0,
) -> float:
    """Truncated first moment sum_{k=0}^s k P(X = k), not E[min(X,s)].

    Uses truncated-mean identities to avoid repeated PMF summation in high-stock
    NB sensitivity runs: for Poisson, E[X 1{X<=s}] = mu F(s-1); for the
    scipy NB parameterisation, E[X 1{X<=s}] = mu F_{n+1,p}(s-1).
    """
    if stock_level <= 0 or expected_demand <= 0.0:
        return 0.0
    if demand_model == "negbin" and nb_alpha > 0.0:
        n, p = _nb_n_p(expected_demand, nb_alpha)
        return float(expected_demand * nbinom.cdf(stock_level - 1, n + 1.0, p))
    return float(expected_demand * poisson_cdf(stock_level - 1, expected_demand))


def expected_backorders(
    stock_level: int,
    expected_demand: float,
    *,
    demand_model: DemandModel = "poisson",
    nb_alpha: float = 0.0,
) -> float:
    """Expected backorders EBO at a given stock level."""
    if demand_model == "negbin" and nb_alpha > 0.0:
        n, p = _nb_n_p(expected_demand, nb_alpha)
        tail_moment = expected_demand * nbinom.sf(stock_level - 1, n + 1, p)
        tail = nbinom.sf(stock_level, n, p)
    else:
        tail_moment = expected_demand * poisson.sf(stock_level - 1, expected_demand)
        tail = poisson.sf(stock_level, expected_demand)
    return max(0.0, float(tail_moment - stock_level * tail))


def immediate_fill_rate(stock_level: int, expected_demand: float, *,
                        demand_model: DemandModel = "poisson", nb_alpha: float = 0.0) -> float:
    """P(X < s); service probability only if X is the arrival-seen pipeline.

    A marginal NB pipeline alone does not establish this arrival interpretation.
    """
    return demand_cdf(stock_level - 1, expected_demand,
                      demand_model=demand_model, nb_alpha=nb_alpha)


def select_part_to_stock(
    part_list: List[Part],
    stock: List[int],
    pipeline: List[float],
    use_cost_weighting: bool,
    *,
    demand_model: DemandModel = "poisson",
    nb_alpha: float = 0.0,
    max_stock_level: int = MAX_STOCK_LEVEL,
    remaining_budget: float = float("inf"),
    eligible_indices: set[int] | None = None,
) -> Tuple[int, List[float], bool]:
    """Greedy selection of the part whose stock should increase next."""
    best_index = -1
    best_benefit = 0.0
    current_ebos = [expected_backorders(level, D, demand_model=demand_model,
                       nb_alpha=nb_alpha) for level, D in zip(stock, pipeline)]
    overflow = False

    for index, part in enumerate(part_list):
        if eligible_indices is not None and index not in eligible_indices:
            continue
        if stock[index] >= max_stock_level or part.cost > remaining_budget:
            continue

        ebo_at_next = expected_backorders(
            stock[index] + 1,
            pipeline[index],
            demand_model=demand_model,
            nb_alpha=nb_alpha,
        )
        ebo_at_current = expected_backorders(
            stock[index],
            pipeline[index],
            demand_model=demand_model,
            nb_alpha=nb_alpha,
        )
        current_ebos[index] = ebo_at_current

        benefit = max(0.0, ebo_at_current - ebo_at_next)
        if use_cost_weighting:
            benefit /= part.cost

        if benefit > best_benefit:
            best_benefit = benefit
            best_index = index

    return best_index, current_ebos, overflow


def _system_operating_time(base: Base, part_list: List[Part]) -> float:
    failure_rate = sum(
        part.lambda_ * base.duty_cycle * base.assets * part.qpa for part in part_list
    )
    if failure_rate <= 0:
        return float("inf")
    return 1.0 / failure_rate


def _operational_availability(
    operating_time: float,
    waiting_time: float,
    duty_cycle: float,
) -> Tuple[float, float, float]:
    adjusted_waiting_time = waiting_time * duty_cycle
    if operating_time == float("inf"):
        return 1.0, waiting_time, adjusted_waiting_time
    availability = operating_time / (operating_time + adjusted_waiting_time)
    return availability, waiting_time, adjusted_waiting_time


def _minimum_fill_rate(
    stock: List[int],
    pipeline: List[float],
    *,
    demand_model: DemandModel = "poisson",
    nb_alpha: float = 0.0,
) -> float:
    fill_rates = [
        immediate_fill_rate(
            level,
            pipeline[index],
            demand_model=demand_model,
            nb_alpha=nb_alpha,
        )
        for index, level in enumerate(stock)
    ]
    return min(fill_rates) if fill_rates else 0.0


def _meets_minimum_fill_rate(
    stock: List[int],
    pipeline: List[float],
    minimum_fill_rate: float,
    *,
    demand_model: DemandModel = "poisson",
    nb_alpha: float = 0.0,
) -> bool:
    if minimum_fill_rate <= 0.0:
        return True
    return all(
        immediate_fill_rate(
            level,
            pipeline[index],
            demand_model=demand_model,
            nb_alpha=nb_alpha,
        )
        >= minimum_fill_rate
        for index, level in enumerate(stock)
    )


def solve_metric(
    base: Base,
    part_list: List[Part],
    *,
    use_cost_weighting: bool = False,
    budget: float,
    minimum_fill_rate: float = 0.0,
    constraint_priority: ConstraintPriority = "budget",
    safety_factor: float = 1.0,
    demand_model: DemandModel = "poisson",
    nb_alpha: float = 0.0,
    max_stock_level: int = MAX_STOCK_LEVEL,
    verbose: bool = False,
) -> MetricSolution:
    """
    Run greedy METRIC stock optimisation under budget or fill-rate constraints.

    Returns a structured solution suitable for notebooks, exports, and manuscript tables.
    """
    pipeline, demand_rate = calculate_pipeline_and_demand_rate(
        base, part_list, safety_factor=safety_factor
    )
    stock = [0] * len(part_list)
    total_cost = 0.0
    total_demand_rate = sum(demand_rate)
    operating_time = _system_operating_time(base, part_list)

    trajectory_costs: List[float] = []
    trajectory_ao: List[float] = []
    trajectory_fill_rate: List[float] = []
    previous_minimum_fill_rate = 0.0
    current_ebos = [0.0] * len(part_list)

    if verbose:
        print(f"METRIC optimisation for base {base.name}")
        print(f"  cost weighting: {use_cost_weighting}")
        print(f"  budget: {budget:,.2f}")
        print(f"  minimum fill rate: {minimum_fill_rate:.2f}")
        print(f"  constraint priority: {constraint_priority}")

    while True:
        part_index, current_ebos, overflow = select_part_to_stock(
            part_list,
            stock,
            pipeline,
            use_cost_weighting,
            demand_model=demand_model,
            nb_alpha=nb_alpha,
            max_stock_level=max_stock_level,
            remaining_budget=budget - total_cost if constraint_priority == "budget" else float("inf"),
            eligible_indices={index for index, (level, D) in enumerate(zip(stock, pipeline))
                              if immediate_fill_rate(level, D, demand_model=demand_model,
                                                     nb_alpha=nb_alpha) < minimum_fill_rate}
                             if constraint_priority == "min_fr" else None,
        )
        if constraint_priority == "min_fr" and _meets_minimum_fill_rate(
            stock, pipeline, minimum_fill_rate, demand_model=demand_model, nb_alpha=nb_alpha
        ):
            break
        if overflow or part_index < 0:
            break

        stock[part_index] += 1
        total_cost += part_list[part_index].cost
        current_ebos = [expected_backorders(level, D, demand_model=demand_model,
                        nb_alpha=nb_alpha) for level, D in zip(stock, pipeline)]
        sum_ebo = sum(current_ebos)
        waiting_time = sum_ebo / total_demand_rate if total_demand_rate > 0 else 0.0
        availability, _, _ = _operational_availability(
            operating_time, waiting_time, base.duty_cycle
        )

        minimum_fill_rate_now = _minimum_fill_rate(
            stock,
            pipeline,
            demand_model=demand_model,
            nb_alpha=nb_alpha,
        )
        if minimum_fill_rate_now < previous_minimum_fill_rate:
            minimum_fill_rate_now = previous_minimum_fill_rate

        trajectory_costs.append(total_cost)
        trajectory_ao.append(availability)
        trajectory_fill_rate.append(minimum_fill_rate_now)
        previous_minimum_fill_rate = minimum_fill_rate_now

        if constraint_priority == "min_fr" and _meets_minimum_fill_rate(
            stock,
            pipeline,
            minimum_fill_rate,
            demand_model=demand_model,
            nb_alpha=nb_alpha,
        ):
            break

    if constraint_priority == "min_fr" and not _meets_minimum_fill_rate(
        stock, pipeline, minimum_fill_rate, demand_model=demand_model, nb_alpha=nb_alpha
    ):
        raise ValueError("Minimum fill rate is infeasible within the stock-level limit.")
    current_ebos = [expected_backorders(level, D, demand_model=demand_model,
                    nb_alpha=nb_alpha) for level, D in zip(stock, pipeline)]
    sum_ebo = sum(current_ebos)
    waiting_time = sum_ebo / total_demand_rate if total_demand_rate > 0 else 0.0
    availability, waiting_time, adjusted_waiting_time = _operational_availability(
        operating_time, waiting_time, base.duty_cycle
    )
    grounded_cost = base.grounded * sum_ebo

    part_results = [
        PartStockResult(
            name=part.name,
            stock=stock[index],
            ebo=expected_backorders(
                stock[index],
                pipeline[index],
                demand_model=demand_model,
                nb_alpha=nb_alpha,
            ),
            fill_rate=immediate_fill_rate(
                stock[index],
                pipeline[index],
                demand_model=demand_model,
                nb_alpha=nb_alpha,
            ),
            pipeline=pipeline[index],
            demand_rate=demand_rate[index],
        )
        for index, part in enumerate(part_list)
    ]

    solution = MetricSolution(
        base_name=base.name,
        parts=part_results,
        total_cost=total_cost,
        operational_availability=availability,
        grounded_cost=grounded_cost,
        waiting_time_hours=waiting_time,
        adjusted_waiting_time_hours=adjusted_waiting_time,
        system_mtbf_hours=operating_time,
        sum_ebo=sum_ebo,
        trajectory_costs=trajectory_costs,
        trajectory_ao=trajectory_ao,
        trajectory_fill_rate=trajectory_fill_rate,
    )

    if verbose:
        _print_solution(solution)

    return solution


def _print_solution(solution: MetricSolution) -> None:
    print(f"\nPart\tStock\tEBO\tFill rate")
    for part in solution.parts:
        if part.stock > 0:
            print(f"{part.name}\t{part.stock}\t{part.ebo:.5f}\t{part.fill_rate:.2f}")
    print(f"Estimated grounded daily cost = {solution.grounded_cost:.2f}")
    print(f"Stock cost = {solution.total_cost:,.2f}")
    print(f"Operational availability = {solution.operational_availability:.4f}")


# Backward-compatible aliases for teaching materials and legacy notebooks.
calculatePipelineAndDemandRate = calculate_pipeline_and_demand_rate
getPoissonPMF = poisson_pmf
getWeightedExpectedValue = weighted_expected_demand
getPoissonCDF = poisson_cdf
getExpectedBackorders = expected_backorders
selectOptimalPartToStock = select_part_to_stock
Solve = solve_metric
