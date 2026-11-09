import unittest
import numpy as np
from scipy.stats import poisson, nbinom
from ramsc.metric import expected_backorders, immediate_fill_rate, solve_metric
from ramsc.models import Base, Part


class MetricTests(unittest.TestCase):
    def test_small_tail_relative_accuracy(self):
        for model, alpha, mu, stock in [('poisson', 0, .1, 15),
                                       ('poisson', 0, 2, 50),
                                       ('negbin', .32, .1, 50)]:
            distribution = nbinom(1/alpha, 1/(1+alpha*mu)) if alpha else poisson(mu)
            reference = distribution.sf(np.arange(stock, stock+2000)).sum()
            actual = expected_backorders(stock, mu, demand_model=model, nb_alpha=alpha)
            self.assertGreater(actual, 0)
            self.assertAlmostEqual(actual/reference, 1, places=9)

    def test_independent_tail_sum_and_marginals(self):
        for model, alpha in [('poisson', 0), ('negbin', .32), ('negbin', 16.6)]:
            for mu in [.1, 2, 30]:
                distribution = nbinom(1/alpha, (1/alpha)/(1/alpha+mu)) if alpha else poisson(mu)
                for stock in [0, 1, 3, 15, 50]:
                    kwargs = dict(demand_model=model, nb_alpha=alpha)
                    value = expected_backorders(stock, mu, **kwargs)
                    # E[(X-s)+] = sum_{k=s}^infinity P(X>k), independent of truncated mean.
                    reference = float(distribution.sf(np.arange(stock, 20000)).sum())
                    self.assertAlmostEqual(value, reference, places=8)
                    self.assertAlmostEqual(value-expected_backorders(stock+1, mu, **kwargs),
                                           distribution.sf(stock), places=9)
                    self.assertAlmostEqual(immediate_fill_rate(stock, mu, **kwargs),
                                           distribution.cdf(stock-1), places=12)
                    self.assertGreaterEqual(value, 0)
                self.assertAlmostEqual(expected_backorders(0, mu, **kwargs), mu)
                self.assertEqual(immediate_fill_rate(0, mu, **kwargs), 0)

    def test_solution_totals_budget_and_trajectory(self):
        base = Base(1, 'test', 1, 1, 1, 10)
        parts = [Part('a', 3, .01, 1, 1), Part('b', 7, .02, 1, 1)]
        for budget in [0, 2, 3, 10, 50]:
            result = solve_metric(base, parts, budget=budget, use_cost_weighting=True)
            self.assertLessEqual(result.total_cost, budget)
            self.assertAlmostEqual(result.sum_ebo, sum(p.ebo for p in result.parts))
            self.assertAlmostEqual(result.total_cost, sum(p.stock*q.cost for p,q in zip(result.parts,parts)))
            if result.trajectory_ao:
                self.assertAlmostEqual(result.trajectory_ao[-1], result.operational_availability)
        result = solve_metric(base, parts, budget=0, minimum_fill_rate=.85, constraint_priority='min_fr')
        self.assertGreaterEqual(min(p.fill_rate for p in result.parts), .85)
        for part in result.parts:
            self.assertLess(immediate_fill_rate(part.stock-1, part.pipeline), .85)
        self.assertAlmostEqual(result.sum_ebo, sum(p.ebo for p in result.parts))

    def test_stock_cap_does_not_stop_other_parts(self):
        base = Base(1, 'test', 1, 1, 1, 10)
        parts = [Part('a', 1, .1, 1, 1), Part('b', 1, .01, 1, 1)]
        result = solve_metric(base, parts, budget=10, max_stock_level=1)
        self.assertEqual([p.stock for p in result.parts], [1, 1])

    def test_infeasible_service_target_is_not_a_solution(self):
        base = Base(1, 'test', 1, 1, 1, 10)
        with self.assertRaisesRegex(ValueError, 'infeasible'):
            solve_metric(base, [Part('a', 1, .1, 1, 1)], budget=0,
                         constraint_priority='min_fr', minimum_fill_rate=.95,
                         max_stock_level=1)



if __name__ == '__main__':
    unittest.main()
