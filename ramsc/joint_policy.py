"""Synthetic single-position fleet renewal and shared base-stock simulation."""
from collections import deque
from dataclasses import dataclass
import heapq
import math
import numpy as np


@dataclass(frozen=True)
class JointInputs:
    assets: int = 8
    shape: float = 2.0
    scale: float = 180.0
    lead_days: float = 20.0
    corrective_days: float = 2.0
    preventive_days: float = .5
    part_price: float = 1000.0
    corrective_work_cost: float = 500.0
    preventive_work_cost: float = 150.0
    down_cost_per_day: float = 2000.0
    capital_rate: float = .2
    warmup_days: float = 365.0
    measurement_days: float = 3650.0


def simulate_policy(inputs, age, stock, seed=0, lifetime_draw=None):
    """Age advances in operating days, stopping during downtime; perfect renewal.

    Procurement follows every demand, including preventive replacements. Costs
    are synthetic assumptions. Independent asset streams pair cycle draws.
    """
    p = inputs
    if age <= 0 or stock < 0 or int(stock) != stock or p.assets < 1:
        raise ValueError('positive age/assets and non-negative integer stock required')
    if p.shape <= 0 or p.scale <= 0 or p.measurement_days <= 0:
        raise ValueError('positive lifetime and measurement parameters required')
    if any(v < 0 for v in (p.lead_days,p.corrective_days,p.preventive_days,
                           p.part_price,p.corrective_work_cost,p.preventive_work_cost,
                           p.down_cost_per_day,p.capital_rate,p.warmup_days)):
        raise ValueError('times and costs must be non-negative')
    end = p.warmup_days+p.measurement_days
    streams = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(p.assets)]
    events, backlog = [], deque()
    counter = 0
    onhand, pipeline, down = stock, 0, 0
    observed_down = 0.0
    demand_count = immediate = failures = preventive = 0
    procurement = work_cost = 0.0
    last = 0.0
    all_demands = arrivals = fulfilled = 0

    def push(time, kind, asset, failure=False):
        nonlocal counter
        counter += 1
        heapq.heappush(events,(time,kind,counter,asset,failure))

    def renewal(time, asset):
        life = lifetime_draw(asset) if lifetime_draw else p.scale*streams[asset].weibull(p.shape)
        if life <= 0 or not math.isfinite(life):
            raise ValueError('lifetimes must be finite and positive')
        push(time+min(age,life),2,asset,life <= age)

    def service(time, asset, failure):
        nonlocal fulfilled
        fulfilled += 1
        push(time+(p.corrective_days if failure else p.preventive_days),1,asset)

    for asset in range(p.assets):
        renewal(0.0,asset)
    while events:
        time,kind,_,asset,failure = heapq.heappop(events)
        if time > end:
            break
        observed_down += down*max(0.,time-max(last,p.warmup_days))
        last = time
        if kind == 0:  # A replenishment arrival; FIFO for outstanding demands.
            pipeline -= 1
            arrivals += 1
            if backlog:
                waiting_asset,waiting_failure = backlog.popleft()
                service(time,waiting_asset,waiting_failure)
            else:
                onhand += 1
        elif kind == 1:
            down -= 1
            renewal(time,asset)
        else:
            down += 1
            all_demands += 1
            available = onhand > 0
            if p.warmup_days <= time < end:
                demand_count += 1
                immediate += int(available)
                failures += int(failure)
                preventive += int(not failure)
                procurement += p.part_price
                work_cost += p.corrective_work_cost if failure else p.preventive_work_cost
            pipeline += 1
            push(time+p.lead_days,0,asset)
            if available:
                onhand -= 1
                service(time,asset,failure)
            else:
                backlog.append((asset,failure))
        assert onhand+pipeline-len(backlog) == stock
        assert all_demands == fulfilled+len(backlog)
        assert pipeline == all_demands-arrivals
        assert 0 <= down <= p.assets
    observed_down += down*max(0.,end-max(last,p.warmup_days))
    years = p.measurement_days/365
    capital = stock*p.part_price*p.capital_rate*years
    down_cost = observed_down*p.down_cost_per_day
    return dict(age_days=age,stock=stock,seed=seed,
                annual_cost=(procurement+work_cost+down_cost+capital)/years,
                annual_procurement=procurement/years,annual_work_cost=work_cost/years,
                annual_down_cost=down_cost/years,annual_capital_charge=capital/years,
                annual_down_asset_days=observed_down/years,
                availability=1-observed_down/(p.assets*p.measurement_days),
                immediate_fraction=immediate/demand_count if demand_count else float('nan'),
                failures=failures,preventive=preventive,demands=demand_count,
                initial_stock_investment=stock*p.part_price)
