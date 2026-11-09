import unittest
import numpy as np
import pandas as pd
from ramsc.decision_priority import consequence_priority


class PriorityTests(unittest.TestCase):
    def test_decomposition_counts_frequency_once(self):
        events = np.array([10., 20.])
        work, cost, hours = np.array([40., 100.]), np.array([200., 800.]), 1000.
        table = pd.DataFrame(dict(removal_rate=events/hours,
                                  labour_per_event=work/events,
                                  parts_cost_per_event=cost/events))
        actual = consequence_priority(table, labour_weight=.3,
                                      labour_reference=5, parts_reference=100)
        np.testing.assert_allclose(actual, .3*work/(hours*5)+.7*cost/(hours*100))

    def test_missing_is_not_zero_or_renormalised(self):
        table = pd.DataFrame(dict(removal_rate=[.1, 0., .1],
                                  labour_per_event=[np.nan, np.nan, 0.],
                                  parts_cost_per_event=[10., 10., 10.]))
        interior = consequence_priority(table, labour_weight=.5,
                                        labour_reference=1, parts_reference=10)
        self.assertTrue(interior.iloc[:2].isna().all())
        self.assertEqual(interior.iloc[2], .05)
        endpoint = consequence_priority(table, labour_weight=0,
                                        labour_reference=1, parts_reference=10)
        np.testing.assert_allclose(endpoint, [.1, 0., .1])

    def test_invalid_preferences_and_scales(self):
        table = pd.DataFrame(dict(removal_rate=[.1], labour_per_event=[2.],
                                  parts_cost_per_event=[10.]))
        for weight in (-.1, 1.1, np.nan):
            with self.assertRaises(ValueError):
                consequence_priority(table, labour_weight=weight,
                                     labour_reference=1, parts_reference=10)
        with self.assertRaises(ValueError):
            consequence_priority(table, labour_weight=.5, labour_reference=0,
                                 parts_reference=10)


if __name__ == '__main__':
    unittest.main()
