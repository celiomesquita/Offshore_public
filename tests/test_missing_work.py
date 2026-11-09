from itertools import product
import unittest
import numpy as np
from ramsc.missing_work import paired_coverage_bounds, unbounded_paired_coverage


class MissingWorkTests(unittest.TestCase):
    def test_bounds_against_all_vertices(self):
        rng = np.random.default_rng(807)
        for _ in range(40):
            observed = rng.uniform(0, 20, 4)
            upper = rng.uniform(0, 40, 4)
            delta = rng.choice([-1., -.5, 0., .5, 1.], 4)
            vertices = [observed+upper*np.array(v) for v in product([0,1], repeat=4)]
            values = [np.dot(delta,v)/v.sum() for v in vertices]
            actual = paired_coverage_bounds(observed,upper,delta)
            np.testing.assert_allclose(actual,[min(values),max(values)],atol=1e-12)

    def test_no_missing_and_identical_selections(self):
        np.testing.assert_allclose(paired_coverage_bounds([10,20],[0,0],[1,-1]),[-1/3,-1/3])
        self.assertEqual(paired_coverage_bounds([10,20],[100,100],[0,0]),(0.,0.))

    def test_invalid_denominator(self):
        with self.assertRaises(ValueError):
            paired_coverage_bounds([0,0],[10,10],[1,-1])

    def test_unbounded_limits_and_observed_floor(self):
        self.assertEqual(unbounded_paired_coverage([10,20],[1,1],[1,-1]),(-1.,1.))
        np.testing.assert_allclose(unbounded_paired_coverage([10,20],[0,1],[1,-1]),[-1.,-1/3])
        lo,hi = paired_coverage_bounds([10,20],[1e9,1e9],[1,-1])
        self.assertAlmostEqual(lo,-1.,places=6)
        self.assertAlmostEqual(hi,1.,places=6)


if __name__ == '__main__':
    unittest.main()
