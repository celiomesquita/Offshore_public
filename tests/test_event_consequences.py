import unittest
import numpy as np
import pandas as pd
from scripts.build_revision_event_consequences import allocate_document_work
from scripts.run_revision_priority_backtest import fractional_top_k


class ConsequenceTests(unittest.TestCase):
    def test_conservation_missing_work_and_late_signoff(self):
        events = pd.DataFrame({'doc':['a','a','b','c'],
                               'removed':pd.to_datetime(['2024-01-01']*4)})
        tasks = pd.DataFrame({'doc':['a','a','b','b','c'],
                              'work':[2.,6.,3.,np.nan,5.],
                              'signed':pd.to_datetime(['2024-01-02','2024-02-02',
                                                       '2024-01-03','2024-01-03',None])})
        result, docs = allocate_document_work(events,tasks)
        np.testing.assert_allclose(result.labour_per_event.iloc[:2],[4.,4.])
        self.assertEqual(result.labour_per_event.sum(),8.)
        self.assertTrue(result.labour_per_event.iloc[2:].isna().all())
        self.assertEqual(docs.loc['a','available'],pd.Timestamp('2024-02-02'))
        self.assertTrue(pd.isna(docs.loc['b','available']))

    def test_boundary_ties_preserve_selection_size(self):
        result = fractional_top_k(pd.Series([10.,8.,8.,8.,1.]), k=3)
        np.testing.assert_allclose(result,[1.,2/3,2/3,2/3,0.])
        self.assertAlmostEqual(result.sum(),3.)


if __name__ == '__main__':
    unittest.main()
